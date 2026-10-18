//! Phase-control firmware for the 220 Vac halogen dimmer.
//!
//! - ZC (GPIO3): H11AA1 output with the internal pull-up. It is low while the
//!   mains voltage is high and pulses high around every zero crossing, so the
//!   middle of each pulse is the true zero crossing.
//! - FIRE (GPIO4): drives the MOC3052 LED through Q1. High fires the TRIAC.
//!
//! Safety behaviour:
//! - The lamp is off at every boot, and the level is never stored.
//! - Firing needs `LOCK_HALF_CYCLES` consecutive valid zero crossings. Any
//!   invalid or missing crossing stops firing until the lock is regained.
//! - A firing pulse is skipped rather than sent late, so a delayed pulse can
//!   never spill into the next half-cycle.
//!
//! Control is over Wi-Fi from a phone, so no cable has to be connected to the
//! board while it is on mains.

use std::ffi::c_void;
use std::ptr;
use std::sync::atomic::{AtomicBool, AtomicPtr, AtomicU32, Ordering::Relaxed};
use std::thread;
use std::time::Duration;

use anyhow::{bail, Result};
use log::info;
use esp_idf_svc::eventloop::EspSystemEventLoop;
use esp_idf_svc::hal::peripherals::Peripherals;
use esp_idf_svc::http::server::{Configuration as HttpConfig, EspHttpServer};
use esp_idf_svc::http::Method;
use esp_idf_svc::io::Write;
use esp_idf_svc::sys::{self, esp};
use esp_idf_svc::wifi::{AccessPointConfiguration, AuthMethod, BlockingWifi, Configuration, EspWifi};

const ZC_GPIO: i32 = 3;
const FIRE_GPIO: i32 = 4;
/// SuperMini blue LED (active low): shows the firmware is alive without a USB cable.
const LED_GPIO: i32 = 8;

/// Accepted ZC pulse width (µs). On the first board the H11AA1 switches very close to
/// zero and the pulses are only 30–100 µs wide (the design estimate was 2.2 ms).
const ZC_WIDTH_US: (u32, u32) = (10, 5_000);
/// Accepted half-period between zero crossings (µs): 40 to 62.5 Hz mains.
const HALF_PERIOD_US: (u32, u32) = (8_000, 12_500);
/// Consecutive valid half-cycles needed before firing.
const LOCK_HALF_CYCLES: u32 = 8;
/// The ZC level is sampled this many times, `ZC_SAMPLE_US` apart, after every edge;
/// the majority decides the level, so short noise spikes are ignored.
const ZC_SAMPLES: u32 = 4;
const ZC_SAMPLE_US: u32 = 2;
/// No ZC edge for this long means mains is gone (µs).
const ZC_TIMEOUT_US: u32 = 30_000;

/// Earliest firing after the zero crossing (µs). The crossing is only known
/// when the ZC pulse ends; this also leaves margin for a wider pulse on another board.
const MIN_DELAY_US: u32 = 1_400;
/// Latest firing, measured back from the next zero crossing (µs).
const MIN_TAIL_US: u32 = 1_500;
/// A pulse that would start later than this before the next crossing is dropped (µs).
const LATE_LIMIT_US: u32 = 1_000;
/// MOC3052 LED pulse length (µs).
const FIRE_PULSE_US: u32 = 150;
/// Optocoupler LED test length (only allowed with no mains present).
const OPTO_TEST: Duration = Duration::from_secs(30);

const AP_SSID: &str = "esp32-dimmer";
const AP_PASS: &str = "dimmer-lab";

/// Firing delay as a fraction of the half-period, 0..=65536.
/// `FRACTION_OFF` never fires; `FRACTION_FULL` keeps FIRE high while locked.
const FRACTION_OFF: u32 = u32::MAX;
const FRACTION_FULL: u32 = 0;

static FRACTION: AtomicU32 = AtomicU32::new(FRACTION_OFF);
static LEVEL: AtomicU32 = AtomicU32::new(0);
static OPTO_TEST_ON: AtomicBool = AtomicBool::new(false);
/// Bumped on every LED test start or stop, so an old timer cannot end a newer test.
static OPTO_TEST_GEN: AtomicU32 = AtomicU32::new(0);

// Zero-cross state. Written only by the ZC interrupt (and reset by the watchdog).
static RISE_US: AtomicU32 = AtomicU32::new(0);
/// Accepted (debounced) ZC level.
static ZC_HIGH: AtomicBool = AtomicBool::new(false);
static LAST_ZERO_US: AtomicU32 = AtomicU32::new(0);
static HALF_US: AtomicU32 = AtomicU32::new(0);
static WIDTH_US: AtomicU32 = AtomicU32::new(0);
static GOOD: AtomicU32 = AtomicU32::new(0);
static EDGES: AtomicU32 = AtomicU32::new(0);
/// Pulses at least `ZC_WIDTH_US.0` wide: real zero-cross pulses, not probe glitches.
static PULSES: AtomicU32 = AtomicU32::new(0);
static LAST_PULSE_US: AtomicU32 = AtomicU32::new(0);
/// Edges whose level did not change after sampling (noise) and pulses rejected as invalid.
static NOISE: AtomicU32 = AtomicU32::new(0);
static INVALID: AtomicU32 = AtomicU32::new(0);
static MISSED: AtomicU32 = AtomicU32::new(0);
/// Extremes over the current one-second window, reset by the main loop.
static WIN_WIDTH: (AtomicU32, AtomicU32) = (AtomicU32::new(u32::MAX), AtomicU32::new(0));
static WIN_HALF: (AtomicU32, AtomicU32) = (AtomicU32::new(u32::MAX), AtomicU32::new(0));
/// Last completed one-second window, as a JSON fragment for /status.
static ZC_STATS: std::sync::Mutex<String> = std::sync::Mutex::new(String::new());
static FIRED: AtomicU32 = AtomicU32::new(0);
static SKIPPED: AtomicU32 = AtomicU32::new(0);

/// The zero crossing the pending firing timer belongs to. A callback that runs after a
/// newer crossing (a delayed esp_timer task) sees a mismatch and does not fire.
static TARGET_ZERO_US: AtomicU32 = AtomicU32::new(0);

static FIRE_TIMER: AtomicPtr<sys::esp_timer> = AtomicPtr::new(ptr::null_mut());

fn now_us() -> u32 {
    // Truncated to 32 bits; all arithmetic below is wrapping, so this wraps safely every 71 min.
    unsafe { sys::esp_timer_get_time() as u32 }
}

fn fire(on: bool) {
    unsafe { sys::gpio_set_level(FIRE_GPIO, on as u32) };
}

fn led(on: bool) {
    unsafe { sys::gpio_set_level(LED_GPIO, !on as u32) };
}

fn locked() -> bool {
    GOOD.load(Relaxed) >= LOCK_HALF_CYCLES
}

/// Stops firing immediately and forgets the zero-cross lock.
fn unlock() {
    GOOD.store(0, Relaxed);
    let timer = FIRE_TIMER.load(Relaxed);
    if !timer.is_null() {
        unsafe { sys::esp_timer_stop(timer) };
    }
    fire(false);
}

/// ZC edge interrupt.
unsafe extern "C" fn zc_isr(_: *mut c_void) {
    let now = now_us();
    EDGES.fetch_add(1, Relaxed);

    let mut ones = 0;
    for _ in 0..ZC_SAMPLES {
        ones += sys::gpio_get_level(ZC_GPIO) as u32;
        sys::esp_rom_delay_us(ZC_SAMPLE_US);
    }
    let high = 2 * ones > ZC_SAMPLES;
    if ZC_HIGH.swap(high, Relaxed) == high {
        // The level did not really change: a spike or a bounce on a slow edge.
        NOISE.fetch_add(1, Relaxed);
        return;
    }
    if high {
        RISE_US.store(now, Relaxed);
        return;
    }

    // Falling edge: the pulse just ended; its middle is the zero crossing.
    let width = now.wrapping_sub(RISE_US.load(Relaxed));
    WIN_WIDTH.0.fetch_min(width, Relaxed);
    WIN_WIDTH.1.fetch_max(width, Relaxed);
    if width < ZC_WIDTH_US.0 {
        // Too short to be a zero-cross pulse: switching noise on a slow edge. Ignore it.
        return;
    }
    LAST_PULSE_US.store(now, Relaxed);
    PULSES.fetch_add(1, Relaxed);
    if OPTO_TEST_ON.swap(false, Relaxed) {
        // Mains appeared during the LED test: end it at once.
        fire(false);
    }
    let zero = RISE_US.load(Relaxed).wrapping_add(width / 2);
    let half = zero.wrapping_sub(LAST_ZERO_US.swap(zero, Relaxed));
    WIDTH_US.store(width, Relaxed);
    WIN_HALF.0.fetch_min(half, Relaxed);
    WIN_HALF.1.fetch_max(half, Relaxed);

    // One missed pulse doubles the measured half-period. The zero crossing just seen is
    // still real, so keep the lock and use half of it.
    let in_range = |h: u32| (HALF_PERIOD_US.0..=HALF_PERIOD_US.1).contains(&h);
    let half = if locked() && !in_range(half) && in_range(half / 2) {
        MISSED.fetch_add(1, Relaxed);
        half / 2
    } else {
        half
    };
    HALF_US.store(half, Relaxed);
    let valid = width <= ZC_WIDTH_US.1 && in_range(half);
    if !valid {
        INVALID.fetch_add(1, Relaxed);
        unlock();
        return;
    }
    let good = GOOD.load(Relaxed);
    if good < LOCK_HALF_CYCLES {
        GOOD.store(good + 1, Relaxed);
        fire(false);
        return;
    }

    match FRACTION.load(Relaxed) {
        FRACTION_OFF => fire(false),
        FRACTION_FULL => fire(true),
        fraction => {
            fire(false);
            let delay = ((fraction as u64 * half as u64) >> 16) as u32;
            let delay = delay.clamp(MIN_DELAY_US, half - MIN_TAIL_US);
            let elapsed = now.wrapping_sub(zero);
            if delay > elapsed + 100 {
                TARGET_ZERO_US.store(zero, Relaxed);
                sys::esp_timer_start_once(FIRE_TIMER.load(Relaxed), (delay - elapsed) as u64);
            } else {
                SKIPPED.fetch_add(1, Relaxed);
            }
        }
    }
}

/// Firing timer callback (esp_timer task, high priority).
unsafe extern "C" fn fire_cb(_: *mut c_void) {
    let zero = LAST_ZERO_US.load(Relaxed);
    let since_zero = now_us().wrapping_sub(zero);
    let half = HALF_US.load(Relaxed);
    let fraction = FRACTION.load(Relaxed);
    let stale = zero != TARGET_ZERO_US.load(Relaxed);
    if !locked() || fraction == FRACTION_OFF || stale || since_zero > half.saturating_sub(LATE_LIMIT_US) {
        SKIPPED.fetch_add(1, Relaxed);
        return;
    }
    fire(true);
    sys::esp_rom_delay_us(FIRE_PULSE_US);
    fire(false);
    FIRED.fetch_add(1, Relaxed);
}

/// Power fraction (0..=1) of a resistive load fired at angle `alpha` (radians).
fn power_at(alpha: f64) -> f64 {
    use std::f64::consts::PI;
    1.0 - alpha / PI + (2.0 * alpha).sin() / (2.0 * PI)
}

/// Sets the lamp power in percent: 0 = off, 100 = full, otherwise phase control.
fn set_level(percent: u32) {
    let percent = percent.min(100);
    let fraction = match percent {
        0 => FRACTION_OFF,
        100 => FRACTION_FULL,
        p => {
            // Solve power_at(alpha) = p by bisection; power falls as alpha grows.
            let target = p as f64 / 100.0;
            let (mut lo, mut hi) = (0.0, std::f64::consts::PI);
            for _ in 0..40 {
                let mid = (lo + hi) / 2.0;
                if power_at(mid) > target {
                    lo = mid;
                } else {
                    hi = mid;
                }
            }
            ((lo / std::f64::consts::PI) * 65536.0) as u32
        }
    };
    // A level change ends the LED test, so the page never shows a test that is not running.
    stop_opto_test();
    LEVEL.store(percent, Relaxed);
    FRACTION.store(fraction, Relaxed);
    if fraction == FRACTION_OFF {
        fire(false);
    }
}

fn setup_gpio() -> Result<()> {
    unsafe {
        // FIRE first, as an output driven low, before anything else starts.
        esp!(sys::gpio_config(&sys::gpio_config_t {
            pin_bit_mask: 1 << FIRE_GPIO,
            mode: sys::gpio_mode_t_GPIO_MODE_OUTPUT,
            pull_up_en: sys::gpio_pullup_t_GPIO_PULLUP_DISABLE,
            pull_down_en: sys::gpio_pulldown_t_GPIO_PULLDOWN_ENABLE,
            intr_type: sys::gpio_int_type_t_GPIO_INTR_DISABLE,
        }))?;
        fire(false);

        esp!(sys::gpio_config(&sys::gpio_config_t {
            pin_bit_mask: 1 << LED_GPIO,
            mode: sys::gpio_mode_t_GPIO_MODE_OUTPUT,
            pull_up_en: sys::gpio_pullup_t_GPIO_PULLUP_DISABLE,
            pull_down_en: sys::gpio_pulldown_t_GPIO_PULLDOWN_DISABLE,
            intr_type: sys::gpio_int_type_t_GPIO_INTR_DISABLE,
        }))?;
        led(false);

        esp!(sys::gpio_config(&sys::gpio_config_t {
            pin_bit_mask: 1 << ZC_GPIO,
            mode: sys::gpio_mode_t_GPIO_MODE_INPUT,
            pull_up_en: sys::gpio_pullup_t_GPIO_PULLUP_ENABLE,
            pull_down_en: sys::gpio_pulldown_t_GPIO_PULLDOWN_DISABLE,
            intr_type: sys::gpio_int_type_t_GPIO_INTR_ANYEDGE,
        }))?;
        ZC_HIGH.store(sys::gpio_get_level(ZC_GPIO) == 1, Relaxed);

        let mut timer: sys::esp_timer_handle_t = ptr::null_mut();
        esp!(sys::esp_timer_create(
            &sys::esp_timer_create_args_t {
                callback: Some(fire_cb),
                arg: ptr::null_mut(),
                dispatch_method: sys::esp_timer_dispatch_t_ESP_TIMER_TASK,
                name: c"fire".as_ptr(),
                skip_unhandled_events: true,
            },
            &mut timer,
        ))?;
        FIRE_TIMER.store(timer, Relaxed);

        esp!(sys::gpio_install_isr_service(0))?;
        esp!(sys::gpio_isr_handler_add(ZC_GPIO, Some(zc_isr), ptr::null_mut()))?;
    }
    Ok(())
}

fn status_json() -> String {
    let half = HALF_US.load(Relaxed);
    let since_pulse = now_us().wrapping_sub(LAST_PULSE_US.load(Relaxed));
    let mains = PULSES.load(Relaxed) > 0 && since_pulse < ZC_TIMEOUT_US;
    let fraction = FRACTION.load(Relaxed);
    let delay_us = match fraction {
        FRACTION_OFF | FRACTION_FULL => 0,
        f if mains && half >= HALF_PERIOD_US.0 => {
            (((f as u64 * half as u64) >> 16) as u32).clamp(MIN_DELAY_US, half - MIN_TAIL_US)
        }
        _ => 0,
    };
    let freq = if mains && half > 0 { 500_000.0 / half as f32 } else { 0.0 };
    format!(
        "{{\"level\":{},\"mains\":{},\"locked\":{},\"freq_hz\":{:.2},\"zc_width_us\":{},\"delay_us\":{},\"fired\":{},\"skipped\":{},\"opto_test\":{},{}}}",
        LEVEL.load(Relaxed),
        mains,
        mains && locked(),
        freq,
        if mains { WIDTH_US.load(Relaxed) } else { 0 },
        delay_us,
        FIRED.load(Relaxed),
        SKIPPED.load(Relaxed),
        OPTO_TEST_ON.load(Relaxed),
        match ZC_STATS.lock().unwrap().as_str() {
            "" => "\"zc\":null",
            stats => stats,
        },
    )
}

/// Turns FIRE on for a few seconds to check the MOC3052 LED current, only with no mains.
fn start_opto_test() -> Result<()> {
    let since_pulse = now_us().wrapping_sub(LAST_PULSE_US.load(Relaxed));
    if PULSES.load(Relaxed) > 0 && since_pulse < 1_000_000 {
        bail!("mains detected: the LED test only runs with mains disconnected");
    }
    if OPTO_TEST_ON.load(Relaxed) {
        bail!("the LED test is already running");
    }
    let generation = OPTO_TEST_GEN.fetch_add(1, Relaxed) + 1;
    OPTO_TEST_ON.store(true, Relaxed);
    fire(true);
    thread::spawn(move || {
        thread::sleep(OPTO_TEST);
        if OPTO_TEST_GEN.load(Relaxed) == generation && OPTO_TEST_ON.swap(false, Relaxed) {
            fire(false);
        }
    });
    Ok(())
}

fn stop_opto_test() {
    OPTO_TEST_GEN.fetch_add(1, Relaxed);
    if OPTO_TEST_ON.swap(false, Relaxed) {
        fire(false);
    }
}

static INDEX_HTML: &str = include_str!("index.html");

/// Commands must carry `X-Dimmer: 1`. Another web page open on the phone cannot add a
/// custom header to a cross-origin request without a CORS preflight, which this server
/// never answers, so it cannot switch the lamp.
fn from_page(req: &esp_idf_svc::http::server::Request<&mut esp_idf_svc::http::server::EspHttpConnection>) -> bool {
    req.header("X-Dimmer") == Some("1")
}

fn main() -> Result<()> {
    esp_idf_svc::sys::link_patches();
    // Log with `info!`, never `println!`: without a USB host the USB serial console
    // returns an error, and `println!` panics on it (a reset loop on a phone charger).
    esp_idf_svc::log::EspLogger::initialize_default();

    setup_gpio()?;
    // Three quick flashes mark a boot, so repeated resets (a weak supply) are easy to see.
    for _ in 0..3 {
        led(true);
        thread::sleep(Duration::from_millis(80));
        led(false);
        thread::sleep(Duration::from_millis(120));
    }
    set_level(0);

    let peripherals = Peripherals::take()?;
    let sys_loop = EspSystemEventLoop::take()?;
    // No NVS: nothing is written to flash at run time, so the ZC interrupt is never
    // paused by a flash write.
    let mut wifi = BlockingWifi::wrap(EspWifi::new(peripherals.modem, sys_loop.clone(), None)?, sys_loop)?;
    wifi.set_configuration(&Configuration::AccessPoint(AccessPointConfiguration {
        ssid: AP_SSID.try_into().unwrap(),
        password: AP_PASS.try_into().unwrap(),
        auth_method: AuthMethod::WPA2Personal,
        channel: 6,
        max_connections: 4,
        ..Default::default()
    }))?;
    wifi.start()?;
    // Many ESP32-C3 SuperMini boards have a poorly matched antenna and transmit garbage
    // at full power; 8.5 dBm (units of 0.25 dBm) is reliable and plenty for a lab bench.
    esp!(unsafe { sys::esp_wifi_set_max_tx_power(34) })?;
    wifi.wait_netif_up()?;
    let ip = wifi.wifi().ap_netif().get_ip_info()?.ip;
    info!("Access point `{AP_SSID}` (password `{AP_PASS}`): open http://{ip}");

    let mut server = EspHttpServer::new(&HttpConfig {
        stack_size: 8192,
        ..Default::default()
    })?;
    server.fn_handler("/", Method::Get, |req| {
        req.into_response(200, None, &[("Content-Type", "text/html; charset=utf-8")])?
            .write_all(INDEX_HTML.as_bytes())
    })?;
    server.fn_handler("/status", Method::Get, |req| {
        req.into_response(200, None, &[("Content-Type", "application/json"), ("Cache-Control", "no-store")])?
            .write_all(status_json().as_bytes())
    })?;
    // POST /level?p=0..100
    server.fn_handler("/level", Method::Post, |req| {
        if !from_page(&req) {
            return req.into_status_response(403)?.write_all(b"missing X-Dimmer header");
        }
        let query = req.uri().split_once('?').map_or("", |(_, q)| q);
        let level = query.split('&').find_map(|kv| kv.strip_prefix("p=")).and_then(|v| v.parse::<u32>().ok());
        match level {
            Some(p) if p <= 100 => {
                set_level(p);
                req.into_ok_response()?.write_all(b"ok")
            }
            _ => req.into_status_response(400)?.write_all(b"expected p=0..100"),
        }
    })?;
    server.fn_handler("/opto-test", Method::Post, |req| {
        if !from_page(&req) {
            return req.into_status_response(403)?.write_all(b"missing X-Dimmer header");
        }
        match start_opto_test() {
            Ok(()) => req.into_ok_response()?.write_all(b"ok"),
            Err(e) => req.into_status_response(409)?.write_all(e.to_string().as_bytes()),
        }
    })?;
    server.fn_handler("/opto-stop", Method::Post, |req| {
        stop_opto_test();
        req.into_ok_response()?.write_all(b"ok")
    })?;

    // Watchdog: losing the zero-cross signal stops firing within ZC_TIMEOUT_US.
    let mut last_print = 0u32;
    let mut last_window = 0u32;
    let mut counts = [0u32; 5];
    loop {
        let now = now_us();
        // Judged on real pulses: noise edges alone must not keep the lock alive.
        if locked() && now.wrapping_sub(LAST_PULSE_US.load(Relaxed)) > ZC_TIMEOUT_US {
            unlock();
            info!("zero-cross lost: firing stopped");
        }
        if now.wrapping_sub(last_window) >= 1_000_000 {
            last_window = now;
            let total = [
                EDGES.load(Relaxed),
                PULSES.load(Relaxed),
                NOISE.load(Relaxed),
                INVALID.load(Relaxed),
                MISSED.load(Relaxed),
            ];
            let d: Vec<u32> = total.iter().zip(counts).map(|(t, c)| t.wrapping_sub(c)).collect();
            counts = total;
            let ext = |w: &(AtomicU32, AtomicU32)| {
                let (lo, hi) = (w.0.swap(u32::MAX, Relaxed), w.1.swap(0, Relaxed));
                if hi == 0 { (0, 0) } else { (lo, hi) }
            };
            let (w, h) = (ext(&WIN_WIDTH), ext(&WIN_HALF));
            *ZC_STATS.lock().unwrap() = format!(
                "\"zc\":{{\"edges\":{},\"pulses\":{},\"noise\":{},\"invalid\":{},\"missed\":{},\"width_min\":{},\"width_max\":{},\"half_min\":{},\"half_max\":{}}}",
                d[0], d[1], d[2], d[3], d[4], w.0, w.1, h.0, h.1
            );
        }
        // Heartbeat once the access point is up: a short flash every second.
        led(now % 1_000_000 < 50_000);
        if now.wrapping_sub(last_print) > 2_000_000 {
            last_print = now;
            info!("{}", status_json());
        }
        thread::sleep(Duration::from_millis(10));
    }
}
