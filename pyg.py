import pyglet
from pyglet import gl
from pyglet.window import key

import time, math


class State(object):
    def __init__(self):
        self.ghost_x = 1
        self.ghost_y = 0
        self.vx = 0
        self.vy = 0
        self.base_acc = 0
        self.direction = 0

    @property
    def rotation(self):
        return 5 * math.sin((time.time() % 2) * math.pi)
    
    def accelerate(self, dir):
        self.base_acc += dir

    def jump(self):
        if self.ghost_y == 0:
            self.vy = 10

    def update(self, dt, acc_x, acc_y):
        if acc_x is None:
            base_acc = max(1, min(-1, self.base_acc))
            ax = 20 * base_acc
        else:
            ax = 20 * acc_x

        self.vx += dt * ax

        self.vx = max(min(self.vx, 20), -20)
        if self.vx > 0:
            self.vx -= dt * 12
            if self.vx < 0:
                self.vx = 0
        elif self.vx < 0:
            self.vx += dt * 12
            if self.vx > 0:
                self.vx = 0
        
        if self.vx > 0.1:
            self.direction = 1
        elif self.vx < -0.1:
            self.direction = 0

        self.ghost_x += dt * self.vx

        self.vy -= 15 * dt
        self.ghost_y += dt * self.vy
        if self.ghost_y < 0:
            self.ghost_y = 0
            self.vy = 0



class Viewport(object):
    """Maintain the transform world -> screen so that 

    - viewport in the world has dimentions of roughly 16x9
    - main character is in the screen
    """

    def __init__(self, window):
        self.window = window
        self.offset_x = 0
        self.offset_y = 0
        self.scale = self.window.height / 9
    
    def update(self, x, y):
        self.scale = self.window.height / 9
        scaled_width = self.window.width / self.scale
        if x < self.offset_x + 3 - (16 - scaled_width)/2:
            self.offset_x = x - 3 + (16 - scaled_width)/2
        elif x > self.offset_x + 13 - (16 - scaled_width)/2:
            self.offset_x = x - 13 + (16 - scaled_width)/2
        if y < self.offset_y + 1:
            self.offset_y = y - 1
        elif y > self.offset_y + 8:
            self.offset_y = y - 8
    
    def transform(self, x, y):
        return (x - self.offset_x) * self.scale, (y - self.offset_y) * self.scale


class View(object):
    def __init__(self, state):
        self.state = state
        self.window = pyglet.window.Window(
            config=gl.Config(double_buffer=True), fullscreen=False)
        print('{}x{}'.format(self.window.width, self.window.height))
        self.fps = pyglet.window.FPSDisplay(self.window)
        self.window.set_exclusive_mouse()
        self.viewport = Viewport(self.window)

        self.window.push_handlers(self.on_draw, self.on_key_press, self.on_key_release)
        self.joystick = None
        joysticks = pyglet.input.get_joysticks()
        if joysticks:
            self.joystick = joysticks[0]
            self.joystick.open()
            self.joystick.push_handlers(self)

        ghost_img = pyglet.resource.image('res/ghost.png')
        ghost_seq = pyglet.image.ImageGrid(ghost_img, 1, 2)
        w = ghost_seq[0].width
        ghost_seq[0].anchor_x = w / 2
        ghost_seq[1].anchor_x = w / 2
        self.ghost = [pyglet.sprite.Sprite(img=g, subpixel=True) for g in ghost_seq]
        pyglet.clock.schedule_interval(self.update, 1/240)
    
    def update(self, dt):
        if self.joystick:
            self.state.update(dt, self.joystick.x, self.joystick.y)
        else:
            self.state.update(dt, None, None)

    def on_draw(self):
        self.window.clear()

        gx, gy = (self.state.ghost_x, self.state.ghost_y)
        self.viewport.update(gx, gy)
        gtx, gty = self.viewport.transform(gx, gy)
        ghost = self.ghost[self.state.direction]
        ghost.update(x=gtx, y=gty, rotation=self.state.rotation,
                          scale=self.viewport.scale/16)
        ghost.draw()

        _, ground_y = self.viewport.transform(0, 0)
        pyglet.graphics.draw(
            4, pyglet.gl.GL_QUADS,
            ('v2f', (0, 0,
                     self.window.width, 0,
                     self.window.width, ground_y,
                     0, ground_y)),
            ('c3B', (128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128)))
        self.fps.draw()

    def on_key_press(self, symbol, modifiers):
        print('Pressed: {} {}'.format(symbol, modifiers))
        if symbol == key.F:
            self.window.set_fullscreen(not self.window.fullscreen)
            print('{}x{}'.format(self.window.width, self.window.height))
        elif symbol == key.RIGHT:
            self.state.accelerate(1)
        elif symbol == key.LEFT:
            self.state.accelerate(-1)
        elif symbol == key.SPACE:
            self.state.jump()

    def on_key_release(self, symbol, modifiers):
        print('Released: {} {}'.format(symbol, modifiers))
        if symbol == key.RIGHT:
            self.state.accelerate(-1)
        elif symbol == key.LEFT:
            self.state.accelerate(1)

    def on_joybutton_press(self, joystick, button):
        print('joystick button pressed:', button)
        if button == 0:
            self.state.jump()

    def on_joybutton_release(self, joystick, button):
        print('joystick button released:', button)

    def on_joyhat_motion(self, joystick, hat_x, hat_y):
        print('hat_x:', hat_x, 'hat_y:', hat_y)


def main():
    display = pyglet.canvas.get_display()
    print('display:', display)
    screens = display.get_screens()
    print('screens:', screens)
    joysticks = pyglet.input.get_joysticks()
    print('joysticks:', joysticks)
    state = State()
    view = View(state)
    pyglet.app.run()


if __name__ == '__main__':
    main()
