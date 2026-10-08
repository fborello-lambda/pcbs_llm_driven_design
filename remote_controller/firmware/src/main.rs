//! Remote controller test firmware: shows the thumbstick position and the
//! three buttons on the SSD1306 OLED.
//!
//! At start-up the rest position is taken as the centre. Hold all three buttons
//! for one second to run the on-screen calibration: first the stick is left at
//! rest to measure its centre, then it is moved around the edges to measure its
//! travel.
//!
//! Top: a circle for the thumbstick range with a dot at the current position.
//! Bottom: one square per button, filled while pressed, outlined otherwise.

use std::thread;
use std::time::{Duration, Instant};

use anyhow::{anyhow, Result};
use embedded_graphics::mono_font::ascii::FONT_6X10;
use embedded_graphics::mono_font::MonoTextStyle;
use embedded_graphics::pixelcolor::BinaryColor;
use embedded_graphics::prelude::*;
use embedded_graphics::primitives::{Circle, PrimitiveStyle, Rectangle};
use embedded_graphics::text::{Alignment, Text};
use esp_idf_svc::hal::adc::attenuation;
use esp_idf_svc::hal::adc::oneshot::config::{AdcChannelConfig, Calibration};
use esp_idf_svc::hal::adc::oneshot::{AdcChannelDriver, AdcDriver};
use esp_idf_svc::hal::adc::Resolution;
use esp_idf_svc::hal::gpio::{PinDriver, Pull};
use esp_idf_svc::hal::i2c::{I2cConfig, I2cDriver};
use esp_idf_svc::hal::peripherals::Peripherals;
use esp_idf_svc::hal::units::Hertz;
use ssd1306::prelude::*;
use ssd1306::mode::BufferedGraphicsMode;
use ssd1306::{I2CDisplayInterface, Ssd1306};

type Display<DI> = Ssd1306<DI, DisplaySize128x64, BufferedGraphicsMode<DisplaySize128x64>>;

// Orientation of the mounted thumbstick, checked on the board: the JOY_X channel
// follows up/down and JOY_Y follows left/right, both reversed.
// Swap the axes if the dot moves sideways when the stick moves up/down;
// flip an INVERT if the dot moves the opposite way along that screen axis.
const SWAP_AXES: bool = true;
const INVERT_X: bool = true; // screen horizontal, right = positive
const INVERT_Y: bool = true; // screen vertical, up = positive

/// Radius around the rest position treated as centred (fraction of full travel).
/// The stick does not return to exactly the same spot after a large movement.
const DEAD_ZONE: f32 = 0.10;
/// Travel assumed on each side of centre (mV) when the edges were not reached during calibration.
const DEFAULT_TRAVEL_MV: f32 = 500.0;
/// ADC samples averaged per reading, to reduce noise.
const SAMPLES: u32 = 8;

const SETTLE_TIME: Duration = Duration::from_millis(1500);
const CENTER_SAMPLES: u32 = 50;
const EDGE_TIME: Duration = Duration::from_secs(4);
const FRAME: Duration = Duration::from_millis(30);
/// How long all three buttons must be held to start the calibration.
const CALIBRATION_HOLD: Duration = Duration::from_secs(1);

const STICK_CENTER: Point = Point::new(64, 24);
const STICK_DIAMETER: u32 = 46;
const DOT_DIAMETER: u32 = 9;
const BUTTON_SIZE: u32 = 12;
const BUTTON_Y: i32 = 57;
// Left to right as on the board: ON/SELECT, PRESET, OFF/BACK.
const BUTTON_X: [i32; 3] = [24, 64, 104];

/// One thumbstick axis: centre from the rest calibration, travel from the edge calibration.
struct Axis {
    center: f32,
    low: f32,
    high: f32,
    invert: bool,
}

impl Axis {
    fn new(center: f32, invert: bool) -> Self {
        Self {
            center,
            low: center,
            high: center,
            invert,
        }
    }

    /// Records the furthest positions reached.
    fn extend(&mut self, mv: f32) {
        self.low = self.low.min(mv);
        self.high = self.high.max(mv);
    }

    /// Falls back to a default travel on any side that was not reached during calibration.
    fn finish(&mut self) {
        if self.high - self.center < DEFAULT_TRAVEL_MV / 2.0 {
            self.high = self.center + DEFAULT_TRAVEL_MV;
        }
        if self.center - self.low < DEFAULT_TRAVEL_MV / 2.0 {
            self.low = self.center - DEFAULT_TRAVEL_MV;
        }
    }

    /// Returns the position in -1.0..=1.0 (before the dead zone).
    fn normalize(&mut self, mv: f32) -> f32 {
        self.extend(mv);
        let v = if mv >= self.center {
            (mv - self.center) / (self.high - self.center).max(1.0)
        } else {
            (mv - self.center) / (self.center - self.low).max(1.0)
        };
        let v = v.clamp(-1.0, 1.0);
        if self.invert {
            -v
        } else {
            v
        }
    }
}

/// Applies a circular dead zone and rescales the rest so the edge is still reached.
fn dead_zone(x: f32, y: f32) -> (f32, f32) {
    let m = (x * x + y * y).sqrt();
    if m < DEAD_ZONE {
        return (0.0, 0.0);
    }
    let scale = ((m - DEAD_ZONE) / (1.0 - DEAD_ZONE)).min(1.0) / m;
    (x * scale, y * scale)
}

fn draw_stick<D>(d: &mut D, x: f32, y: f32) -> Result<()>
where
    D: DrawTarget<Color = BinaryColor>,
    D::Error: core::fmt::Debug,
{
    let travel = (STICK_DIAMETER - DOT_DIAMETER) as f32 / 2.0;
    Circle::with_center(STICK_CENTER, STICK_DIAMETER)
        .into_styled(PrimitiveStyle::with_stroke(BinaryColor::On, 1))
        .draw(d)
        .map_err(|e| anyhow!("{e:?}"))?;
    // Screen y grows downwards, so "up" on the stick is a negative offset.
    let dot = STICK_CENTER + Point::new((x * travel).round() as i32, (-y * travel).round() as i32);
    Circle::with_center(dot, DOT_DIAMETER)
        .into_styled(PrimitiveStyle::with_fill(BinaryColor::On))
        .draw(d)
        .map_err(|e| anyhow!("{e:?}"))?;
    Ok(())
}

fn draw_lines<D>(d: &mut D, lines: &[&str], top: i32) -> Result<()>
where
    D: DrawTarget<Color = BinaryColor>,
    D::Error: core::fmt::Debug,
{
    let style = MonoTextStyle::new(&FONT_6X10, BinaryColor::On);
    for (i, line) in lines.iter().enumerate() {
        Text::with_alignment(line, Point::new(64, top + 12 * i as i32), style, Alignment::Center)
            .draw(d)
            .map_err(|e| anyhow!("{e:?}"))?;
    }
    Ok(())
}

/// On-screen calibration: centre with the stick at rest, then travel while circling the edges.
fn calibrate<DI: WriteOnlyDataCommand>(
    display: &mut Display<DI>,
    read_stick: &mut impl FnMut() -> Result<(f32, f32)>,
) -> Result<(Axis, Axis)> {
    // Calibration step 1: centre, with the stick at rest.
    display.clear_buffer();
    draw_lines(display, &["CALIBRATION", "", "Release buttons", "and the stick"], 12)?;
    display.flush().map_err(|e| anyhow!("OLED write failed: {e:?}"))?;
    thread::sleep(SETTLE_TIME);
    let (mut ch, mut cv) = (0.0, 0.0);
    for _ in 0..CENTER_SAMPLES {
        let (h, v) = read_stick()?;
        ch += h;
        cv += v;
        thread::sleep(Duration::from_millis(10));
    }
    let mut x_axis = Axis::new(ch / CENTER_SAMPLES as f32, INVERT_X);
    let mut y_axis = Axis::new(cv / CENTER_SAMPLES as f32, INVERT_Y);

    // Calibration step 2: travel, moving the stick around its edges.
    let start = Instant::now();
    while start.elapsed() < EDGE_TIME {
        let (h, v) = read_stick()?;
        x_axis.extend(h);
        y_axis.extend(v);
        display.clear_buffer();
        draw_lines(display, &["Circle the edges"], 58)?;
        let done = start.elapsed().as_secs_f32() / EDGE_TIME.as_secs_f32();
        Rectangle::new(Point::new(0, 60), Size::new((128.0 * done) as u32, 4))
            .into_styled(PrimitiveStyle::with_fill(BinaryColor::On))
            .draw(display)
            .map_err(|e| anyhow!("{e:?}"))?;
        let (x, y) = (x_axis.normalize(h), y_axis.normalize(v));
        draw_stick(display, x, y)?;
        display.flush().map_err(|e| anyhow!("OLED write failed: {e:?}"))?;
        thread::sleep(FRAME);
    }
    x_axis.finish();
    y_axis.finish();
    println!(
        "calibrated: horizontal {:.0}/{:.0}/{:.0} mV, vertical {:.0}/{:.0}/{:.0} mV (low/centre/high)",
        x_axis.low, x_axis.center, x_axis.high, y_axis.low, y_axis.center, y_axis.high
    );

    Ok((x_axis, y_axis))
}

fn main() -> Result<()> {
    esp_idf_svc::sys::link_patches();
    esp_idf_svc::log::EspLogger::initialize_default();

    let p = Peripherals::take()?;

    // Thumbstick: X on GPIO0, Y on GPIO1, both through the board's resistor dividers.
    let adc = AdcDriver::new(p.adc1)?;
    let adc_config = AdcChannelConfig {
        attenuation: attenuation::DB_12,
        resolution: Resolution::Resolution12Bit,
        calibration: Calibration::Curve,
    };
    let mut joy_x = AdcChannelDriver::new(&adc, p.pins.gpio0, &adc_config)?;
    let mut joy_y = AdcChannelDriver::new(&adc, p.pins.gpio1, &adc_config)?;

    // Returns the averaged (horizontal, vertical) readings in mV, in screen orientation.
    let mut read_stick = || -> Result<(f32, f32)> {
        let (mut sx, mut sy) = (0u32, 0u32);
        for _ in 0..SAMPLES {
            sx += adc.read(&mut joy_x)? as u32;
            sy += adc.read(&mut joy_y)? as u32;
        }
        let (x, y) = (sx as f32 / SAMPLES as f32, sy as f32 / SAMPLES as f32);
        Ok(if SWAP_AXES { (y, x) } else { (x, y) })
    };

    // Buttons switch to GND; use the internal pull-ups.
    let buttons = [
        PinDriver::input(p.pins.gpio10, Pull::Up)?,
        PinDriver::input(p.pins.gpio21, Pull::Up)?,
        PinDriver::input(p.pins.gpio20, Pull::Up)?,
    ];

    // OLED: SSD1306 128x64 at 0x3C, SDA GPIO6, SCL GPIO7. The module has its own pull-ups.
    let i2c = I2cDriver::new(
        p.i2c0,
        p.pins.gpio6,
        p.pins.gpio7,
        &I2cConfig::new().baudrate(Hertz(400_000)),
    )?;
    let mut display = Ssd1306::new(
        I2CDisplayInterface::new(i2c),
        DisplaySize128x64,
        DisplayRotation::Rotate0,
    )
    .into_buffered_graphics_mode();
    display.init().map_err(|e| anyhow!("OLED init failed: {e:?}"))?;
    let flush_err = |e| anyhow!("OLED write failed: {e:?}");

    // Until a calibration is run, take the rest position at start-up as the centre.
    let (mut h, mut v) = (0.0, 0.0);
    for _ in 0..10 {
        let (rh, rv) = read_stick()?;
        h += rh / 10.0;
        v += rv / 10.0;
    }
    let mut x_axis = Axis::new(h, INVERT_X);
    let mut y_axis = Axis::new(v, INVERT_Y);
    x_axis.finish();
    y_axis.finish();
    let mut held_since: Option<Instant> = None;

    let outline = PrimitiveStyle::with_stroke(BinaryColor::On, 1);
    let filled = PrimitiveStyle::with_fill(BinaryColor::On);

    loop {
        // Holding all three buttons starts the calibration.
        if buttons.iter().all(|b| b.is_low()) {
            let since = *held_since.get_or_insert_with(Instant::now);
            if since.elapsed() >= CALIBRATION_HOLD {
                (x_axis, y_axis) = calibrate(&mut display, &mut read_stick)?;
                while buttons.iter().any(|b| b.is_low()) {
                    thread::sleep(FRAME);
                }
                held_since = None;
                continue;
            }
        } else {
            held_since = None;
        }

        let (h, v) = read_stick()?;
        let (x, y) = dead_zone(x_axis.normalize(h), y_axis.normalize(v));

        display.clear_buffer();
        draw_stick(&mut display, x, y)?;
        for (button, cx) in buttons.iter().zip(BUTTON_X) {
            let style = if button.is_low() { filled } else { outline };
            Rectangle::with_center(Point::new(cx, BUTTON_Y), Size::new_equal(BUTTON_SIZE))
                .into_styled(style)
                .draw(&mut display)
                .map_err(|e| anyhow!("{e:?}"))?;
        }
        display.flush().map_err(flush_err)?;
        thread::sleep(FRAME);
    }
}
