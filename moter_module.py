import time
import RPi.GPIO as GPIO


class StepMotor:
    def __init__(self, step_pins=None, delay=0.003):
        if step_pins is None:
            step_pins = [12, 16, 20, 21]

        self.step_pins = step_pins
        self.delay = delay

        self.seq = [
            [1, 0, 0, 1],
            [1, 1, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 1]
        ]

        self.step_count = len(self.seq)
        self.step_counter = 0

        GPIO.setmode(GPIO.BCM)
        for pin in self.step_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)

    def step_once(self, direction=1):
        for pin in range(4):
            GPIO.output(self.step_pins[pin], self.seq[self.step_counter][pin])

        self.step_counter += direction

        if self.step_counter >= self.step_count:
            self.step_counter = 0
        elif self.step_counter < 0:
            self.step_counter = self.step_count - 1

        time.sleep(self.delay)

    def rotate_steps(self, steps=100, direction=1):
        for _ in range(steps):
            self.step_once(direction)

    def stop(self):
        for pin in self.step_pins:
            GPIO.output(pin, False)

    def cleanup(self):
        self.stop()
        GPIO.cleanup()