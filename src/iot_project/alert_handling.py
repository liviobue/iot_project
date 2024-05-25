import typing

import anyio
import RPi.GPIO as GPIO


buttonpin = 18
buzzerpin = 17
nh3_led_red = 23
co_led_red = 24
o2_led_red = 25
led_green = 12


class AlertManager:

    def __init__(self):
        self._nh3_alert = False
        self._co_alert = False
        self._o2_alert = False
        self.nh3_alert_level = 50 # Normally above 50 PPM for a 8-Hour-Shift
        self.co_alert_level = 100 # Normally above 100PPM
        self.o2_alert_level = 20 # Normally below 17%


    def _setup(self):
        GPIO.setmode(GPIO.BCM)  # use LOGICAL GPIO Numbering

        # Green LED
        GPIO.setup(led_green, GPIO.OUT)
        GPIO.output(led_green, GPIO.HIGH)  # make green ledPin output HIGH level

        # NH3-LED
        GPIO.setup(nh3_led_red, GPIO.OUT)  # set the red ledPin to OUTPUT mode
        GPIO.output(nh3_led_red, GPIO.LOW)  # make red ledPin output LOW level

        # CO-LED
        GPIO.setup(co_led_red, GPIO.OUT)  # set the red ledPin to OUTPUT mode
        GPIO.output(co_led_red, GPIO.LOW)  # make red ledPin output LOW level

        # O2-LED
        GPIO.setup(o2_led_red, GPIO.OUT)  # set the red ledPin to OUTPUT mode
        GPIO.output(o2_led_red, GPIO.LOW)  # make red ledPin output LOW level

        # Buzzer-Pin
        GPIO.setup(buzzerpin, GPIO.OUT)  # set buzzerPin to OUTPUT modea

        # Button
        GPIO.setup(
            buttonpin, GPIO.IN, pull_up_down=GPIO.PUD_UP
        )  # set buttonPin to PULL UP INPUT mode
        
    def __enter__(self):
        self._setup()
        
    def __exit__(self, type, value, tb):
        GPIO.cleanup()

    def check_alerts(self, *, ammonia, carbon_monoxide, oxygen):
        # Check if alerts are True
        self._nh3_alert = ammonia>self.nh3_alert_level
        self._co_alert = carbon_monoxide>self.co_alert_level
        self._o2_alert = oxygen<self.o2_alert_level


    async def wait_for_alert_end(
        self, max_wait_time, previous_button_state
    ) -> tuple[typing.Literal["timeout", "button pressed", "no more alert"], bool]:

        with anyio.move_on_after(max_wait_time):  # Runs until max_wait_time is over
            while True:
                current_button_state = GPIO.input(buttonpin) == GPIO.LOW
                if not previous_button_state and current_button_state:
                    return "button pressed", previous_button_state

                if not self._any_alert:
                    return "no more alert", previous_button_state

                previous_button_state = current_button_state
                await anyio.sleep(0.05)

        return "timeout", previous_button_state


    @property
    def _any_alert(self):
        return self._nh3_alert or self._co_alert or self._o2_alert

    async def alert_loop(self):
        """
        Check if an alert is present or not
        If alert is not present: normal mode and 10ms sleep
        If alert is present: LED & Buzzer on and blinking
        """
        while True:

            """NORMAL-MODE"""
            if not self._any_alert:
                self.normal_mode()
                await anyio.sleep(0.1)
                continue

            """ALERT-MODE"""
            GPIO.output(led_green, GPIO.LOW)
            button_state = True

            while True:

                # Blink-On-Phase
                GPIO.output(nh3_led_red, GPIO.HIGH if self._nh3_alert else GPIO.LOW)
                GPIO.output(co_led_red, GPIO.HIGH if self._co_alert else GPIO.LOW)
                GPIO.output(o2_led_red, GPIO.HIGH if self._o2_alert else GPIO.LOW)
                GPIO.output(buzzerpin, GPIO.HIGH)

                result, button_state = await self.wait_for_alert_end(0.4, button_state)
                if result != "timeout":
                    break  # -> to ACKNOWLEDGE-MODE or to Normal-State

                # Blink-Off-Phase
                GPIO.output(nh3_led_red, GPIO.LOW)
                GPIO.output(co_led_red, GPIO.LOW)
                GPIO.output(o2_led_red, GPIO.LOW)
                GPIO.output(buzzerpin, GPIO.LOW)

                result, button_state = await self.wait_for_alert_end(0.4, button_state)
                if result != "timeout":
                    break  # -> to ACKNOWLEDGE-MODE or to Normal-State

            if result == "button pressed":
                """
                ACKNOWLEDGE-MODE:
                - LEDs on, Buzzer off
                - If Button is pressed again: ACKNOWLEDGE-MODE is aborted
                -> alert-mode is reactivated if there is still an alert, otherwise it goes back to normal
                """
                previous_button_state = True  # Button was pressed before
                GPIO.output(buzzerpin, GPIO.LOW)

                while self._any_alert:
                    current_button_state = GPIO.input(buttonpin) == GPIO.LOW

                    if (
                        not previous_button_state and current_button_state
                    ):  # Checks if there was a change from not-pressed to pressed
                        break

                    GPIO.output(nh3_led_red, GPIO.HIGH if self._nh3_alert else GPIO.LOW)
                    GPIO.output(co_led_red, GPIO.HIGH if self._co_alert else GPIO.LOW)
                    GPIO.output(o2_led_red, GPIO.HIGH if self._o2_alert else GPIO.LOW)

                    previous_button_state = current_button_state
                    await anyio.sleep(0.1)


    def normal_mode(self):
        """
        Mode without alert
        """
        GPIO.output(led_green, GPIO.HIGH)
        GPIO.output(nh3_led_red, GPIO.LOW)
        GPIO.output(co_led_red, GPIO.LOW)
        GPIO.output(o2_led_red, GPIO.LOW)
        GPIO.output(buzzerpin, GPIO.LOW)
