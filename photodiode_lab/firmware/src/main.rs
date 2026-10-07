//! Photodiode lab firmware: reads the TIA output on ADC_OUT (GPIO0, ADC1
//! channel 0) and serves the latest reading on a small phone-friendly page.
//! The ADC attenuation can be changed from the page; the resistor values and
//! all range calculations live in the page itself (see docs/MEASUREMENT_RANGE.md).
//!
//! Default Wi-Fi mode is an access point (SSID `photodiode-lab`, password
//! `photodiode`, page at http://192.168.71.1). Building with the `WIFI_SSID`
//! and `WIFI_PASS` environment variables set joins that network instead; the
//! assigned IP is printed on the serial console.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use anyhow::Result;
use esp_idf_svc::eventloop::EspSystemEventLoop;
use esp_idf_svc::hal::adc::attenuation::{self, adc_atten_t};
use esp_idf_svc::hal::adc::oneshot::config::{AdcChannelConfig, Calibration};
use esp_idf_svc::hal::adc::oneshot::{AdcChannelDriver, AdcDriver};
use esp_idf_svc::hal::adc::Resolution;
use esp_idf_svc::hal::peripherals::Peripherals;
use esp_idf_svc::http::server::{Configuration as HttpConfig, EspHttpServer};
use esp_idf_svc::http::Method;
use esp_idf_svc::io::Write;
use esp_idf_svc::nvs::EspDefaultNvsPartition;
use esp_idf_svc::wifi::{
    AccessPointConfiguration, AuthMethod, BlockingWifi, ClientConfiguration, Configuration,
    EspWifi,
};

const SAMPLES_PER_READING: u32 = 32;
const READING_PERIOD: Duration = Duration::from_millis(200);

const AP_SSID: &str = "photodiode-lab";
const AP_PASS: &str = "photodiode";

/// Selectable attenuations with the ESP-IDF recommended ESP32-C3 input range (mV).
const ATTENUATIONS: [(adc_atten_t, &str, u16); 4] = [
    (attenuation::NONE, "0", 750),
    (attenuation::DB_2_5, "2.5", 1050),
    (attenuation::DB_6, "6", 1300),
    (attenuation::DB_12, "12", 2500),
];
const DEFAULT_ATTENUATION: usize = 3;

static INDEX_HTML: &str = include_str!("index.html");

#[derive(Clone, Copy, Default)]
struct Reading {
    raw: u16,
    raw_min: u16,
    raw_max: u16,
    adc_mv: u16,
    atten: usize,
}

fn main() -> Result<()> {
    esp_idf_svc::sys::link_patches();
    esp_idf_svc::log::EspLogger::initialize_default();

    let peripherals = Peripherals::take()?;
    let sys_loop = EspSystemEventLoop::take()?;
    let nvs = EspDefaultNvsPartition::take()?;

    let mut wifi = BlockingWifi::wrap(
        EspWifi::new(peripherals.modem, sys_loop.clone(), Some(nvs))?,
        sys_loop,
    )?;
    start_wifi(&mut wifi)?;

    let latest = Arc::new(Mutex::new(Reading::default()));
    let requested = Arc::new(AtomicUsize::new(DEFAULT_ATTENUATION));

    let mut server = EspHttpServer::new(&HttpConfig {
        stack_size: 8192,
        ..Default::default()
    })?;
    server.fn_handler("/", Method::Get, |req| {
        req.into_response(200, None, &[("Content-Type", "text/html; charset=utf-8")])?
            .write_all(INDEX_HTML.as_bytes())
    })?;
    let shared = latest.clone();
    server.fn_handler("/data", Method::Get, move |req| {
        let json = to_json(*shared.lock().unwrap());
        req.into_response(
            200,
            None,
            &[("Content-Type", "application/json"), ("Cache-Control", "no-store")],
        )?
        .write_all(json.as_bytes())
    })?;
    // POST /atten?db=0|2.5|6|12 selects the attenuation for the next readings.
    let target = requested.clone();
    server.fn_handler("/atten", Method::Post, move |req| {
        let db = req.uri().split("db=").nth(1).unwrap_or("");
        match ATTENUATIONS.iter().position(|(_, name, _)| *name == db) {
            Some(i) => {
                target.store(i, Ordering::Relaxed);
                req.into_ok_response()?.write_all(b"ok")
            }
            None => req
                .into_status_response(400)?
                .write_all(b"expected db=0, 2.5, 6 or 12"),
        }
    })?;

    let adc = AdcDriver::new(peripherals.adc1)?;
    let mut gpio0 = peripherals.pins.gpio0;

    loop {
        let atten = requested.load(Ordering::Relaxed);
        let (attenuation, name, _) = ATTENUATIONS[atten];
        // The channel driver owns the calibration scheme, so it is rebuilt on every change.
        // SAFETY: the reborrowed pin is only used by this driver, which is dropped before
        // the next reborrow and never forgotten.
        let mut pin = AdcChannelDriver::new(
            &adc,
            unsafe { gpio0.reborrow() },
            &AdcChannelConfig {
                attenuation,
                resolution: Resolution::Resolution12Bit,
                calibration: Calibration::Curve,
            },
        )?;
        println!("attenuation {name} dB");

        while requested.load(Ordering::Relaxed) == atten {
            let (mut sum, mut raw_min, mut raw_max) = (0u32, u16::MAX, 0u16);
            for _ in 0..SAMPLES_PER_READING {
                let sample = adc.read_raw(&mut pin)?;
                sum += sample as u32;
                raw_min = raw_min.min(sample);
                raw_max = raw_max.max(sample);
            }
            let raw = ((sum + SAMPLES_PER_READING / 2) / SAMPLES_PER_READING) as u16;
            let reading = Reading {
                raw,
                raw_min,
                raw_max,
                adc_mv: adc.raw_to_mv(&pin, raw)?,
                atten,
            };
            *latest.lock().unwrap() = reading;
            println!("{}", to_json(reading));
            thread::sleep(READING_PERIOD);
        }
    }
}

fn to_json(r: Reading) -> String {
    let (_, name, range_mv) = ATTENUATIONS[r.atten];
    format!(
        "{{\"raw\":{},\"raw_min\":{},\"raw_max\":{},\"adc_mv\":{},\"atten_db\":{},\"range_mv\":{}}}",
        r.raw, r.raw_min, r.raw_max, r.adc_mv, name, range_mv
    )
}

fn start_wifi(wifi: &mut BlockingWifi<EspWifi<'static>>) -> Result<()> {
    match (option_env!("WIFI_SSID"), option_env!("WIFI_PASS")) {
        (Some(ssid), pass) => {
            let pass = pass.unwrap_or("");
            wifi.set_configuration(&Configuration::Client(ClientConfiguration {
                ssid: ssid.try_into().unwrap(),
                password: pass.try_into().unwrap(),
                auth_method: if pass.is_empty() {
                    AuthMethod::None
                } else {
                    AuthMethod::WPA2Personal
                },
                ..Default::default()
            }))?;
            wifi.start()?;
            wifi.connect()?;
            wifi.wait_netif_up()?;
            let ip = wifi.wifi().sta_netif().get_ip_info()?.ip;
            println!("Joined `{ssid}`: open http://{ip}");
        }
        (None, _) => {
            wifi.set_configuration(&Configuration::AccessPoint(AccessPointConfiguration {
                ssid: AP_SSID.try_into().unwrap(),
                password: AP_PASS.try_into().unwrap(),
                auth_method: AuthMethod::WPA2Personal,
                channel: 6,
                ..Default::default()
            }))?;
            wifi.start()?;
            wifi.wait_netif_up()?;
            let ip = wifi.wifi().ap_netif().get_ip_info()?.ip;
            println!("Access point `{AP_SSID}` (password `{AP_PASS}`): open http://{ip}");
        }
    }
    Ok(())
}
