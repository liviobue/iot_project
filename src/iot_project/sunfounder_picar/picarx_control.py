import argparse

import trio

from .sunfounder_controller import SunFounderController


"""
Adapted from https://github.com/sunfounder/sunfounder-controller/blob/master/examples/picarx_control.py
"""

speed_values = [0, 10, 20, 40, 80]
control_history = []


async def car_control_loop(real_picar: bool = True):
    #if real_picar:
    #    import picarx
    #    px = picarx.Picarx()

    sc = SunFounderController()
    sc.set_name("Explorer")
    sc.set_type("PiCar-X")
    sc.start()

    try:
        current_speed = 0
        current_direction = 0
        prev_speed = current_speed
        prev_dir = current_direction
        running = True

        while running:
            k_val = sc.get("K")  # Left Joy-Stick
            q_val = sc.get("Q")  # Right Joy-Stick

            if k_val is not None and q_val is not None:
                _, y = k_val  # y-Value
                x, _ = q_val  # x-Value

                dx = (
                    sc.get("H", 50) - 50
                ) // 5  # Slider for Fine-Adjustment of Stearing

                current_direction = (
                    x * 45 / 100 + dx
                )  # Steuerwinkel muss von -45 bis +45 gehen
                current_speed = y

            if real_picar:
                grayscale_data = px.get_grayscale_data()
                sc.set("D", grayscale_data)

            if real_picar:
                distance = px.get_distance()
                sc.set("F", distance)

                if 0 < distance < 40:
                    current_speed = min(
                        max(-100, current_speed), 10
                    )  # if car is close to a wall, speed-limit is set to 10 when going forward

            sc.set("A", current_speed)

            if current_speed != prev_speed:
                s = current_speed
                if s < 0:
                    if real_picar:
                        px.backward(abs(s))
                    else:
                        print(f"Backward {abs(s)}")
                elif s > 0:
                    if real_picar:
                        px.forward(s)
                    else:
                        print(f"Forward {s}")
                else:
                    if real_picar:
                        px.forward(0)
                    else:
                        print("Stop")
                prev_speed = current_speed

            if current_direction != prev_dir:
                if real_picar:
                    px.set_dir_servo_angle(current_direction)
                else:
                    print(f"Steer {current_direction}")
                prev_dir = current_direction

            await trio.sleep(0.02)

    finally:
        sc.close()


async def main(args):
    async with trio.open_nursery() as nursery:
        nursery.start_soon(car_control_loop, not args.mock)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="recon")
    parser.add_argument("-m", "--mock", default=False, action="store_true")
    args = parser.parse_args()
    trio.run(main, args)
