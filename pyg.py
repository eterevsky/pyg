import pyglet
from pyglet import gl
from pyglet.window import key

import time, math


class BoundingBox(object):
    """Any enity in the world. Specifies a bounding box.
    
    (x0, y0) -- bottom left corner
    (x1, y1) -- top right corner
    """

    def __init__(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def __str__(self):
        return '({}, {}) ({}, {})'.format(self.x0, self.y0, self.x1, self.y1)

    @property
    def center(self):
        return ((self.x1 + self.x0) / 2, (self.y1 + self.y0) / 2)

    def move(self, dx, dy, dt=None):
        if dt is not None:
            dx *= dt
            dy *= dt
        return BoundingBox(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy)

    def overlaps_x(self, other):
        """Checks whether two boxes projection on X axis overlap."""
        return self.x0 < other.x1 and other.x0 < self.x1
    
    def overlaps_y(self, other):
        """Checks whether two boxes projection on X axis overlap."""
        return self.y0 < other.y1 and self.y1 > other.y0
    
    def intersects_with(self, other):
        return self.overlaps_x(other) and self.overlaps_y(other)

    def contains(self, other):
        return (self.x0 <= other.x0 and self.y0 <= other.y0 and
                other.x1 <= self.x1 and other.y1 <= other.y1)


def move_till_first_collision(box, vx, vy, dt, boxes, bounciness=0.0):
    """
    Returns:
        new box, new vx, vy, dt left
    """
    new_box = box.move(vx, vy, dt)
    new_vx, new_vy = vx, vy
    new = True
    new_dt = dt
    first_collision_box = None
    
    while new:
        new = False
        for other in boxes:
            if new_box.intersects_with(other):
                first_collision_box = other
                lo, hi = 0, new_dt
                for i in range(6):
                    mid = (lo + hi) / 2
                    temp_box = box.move(vx, vy, mid)
                    if temp_box.intersects_with(other):
                        hi = mid
                    else:
                        lo = mid
                new_dt = lo
                new_box = box.move(vx, vy, new_dt)
                assert not new_box.intersects_with(other)
                new = True
                break
    
    if first_collision_box is not None:
        if not box.overlaps_x(first_collision_box):
            new_vx = -bounciness * vx
        if not box.overlaps_y(first_collision_box):
            new_vy = -bounciness * vy

    return new_box, new_vx, new_vy, dt - new_dt


def move_and_collide(box, vx, vy, dt, boxes, bounciness=0):
    """Move the box using the velocity and check for collisions.
    If any collision happens, change that component of speed to 
    """
    box, vx, vy, dt = move_till_first_collision(box, vx, vy, dt, boxes, bounciness)
    if dt > 0:
        box, vx, vy, dt = move_till_first_collision(box, vx, vy, dt, boxes, bounciness)
    return box, vx, vy


class State(object):
    def __init__(self):
        self.ghost_box = BoundingBox(0, 0, 1, 1)
        self.boxes = [
            BoundingBox(-100, -100, 7, 0),
            BoundingBox(9, -100, 100, 0),
            BoundingBox(2, 0, 3, 1),
            BoundingBox(4, 0, 6, 2),
        ]

        # If the ghost goes outside this space, it dies.
        self.level_box = BoundingBox(-100, -100, 100, 100)
        self.vx = 0
        self.vy = 0
        self.player_acc = 0
        self.direction = 0
        self.dead = False

    @property
    def rotation(self):
        return 5 * math.sin((time.time() % 2) * math.pi)
    
    def accelerate(self, dir):
        self.player_acc += dir

    def jump(self):
        for box in self.boxes:
            if self.ghost_box.overlaps_x(box) and 0 <= self.ghost_box.y0 - box.y1 < 0.1:
                self.vy = 10

    def update(self, dt, acc_x, acc_y):
        if self.dead: return

        if acc_x is None:
            self.player_acc = min(1, max(-1, self.player_acc))
            ax = 20 * self.player_acc

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

        self.vy -= 15 * dt

        self.ghost_box, self.vx, self.vy = move_and_collide(
            self.ghost_box, self.vx, self.vy, dt, self.boxes, 0)
        
        if not self.level_box.contains(self.ghost_box):
            self.dead = True


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
        old = (self.offset_x, self.offset_y)
        self.scale = self.window.height / 9
        scaled_width = self.window.width / self.scale
        if x < self.offset_x + 3 - (16 - scaled_width) / 2:
            self.offset_x = x - 3 + (16 - scaled_width) / 2
        elif x > self.offset_x + 13 - (16 - scaled_width) / 2:
            self.offset_x = x - 13 + (16 - scaled_width) / 2
        if y < self.offset_y + 1:
            self.offset_y = y - 1
        elif y > self.offset_y + 8:
            self.offset_y = y - 8
        # if old != (self.offset_x, self.offset_y):
        #     print('New offset:', (self.offset_x, self.offset_y))
    
    def transform(self, x, y):
        return (x - self.offset_x) * self.scale, (y - self.offset_y) * self.scale
    

class View(object):
    """Main loop and interface with Pyglet."""

    def __init__(self, state):
        self.state = state
        self.window = pyglet.window.Window(
            config=gl.Config(double_buffer=True), fullscreen=False)
        print('{}x{}'.format(self.window.width, self.window.height))

        self.fps = pyglet.window.FPSDisplay(self.window)
        self.fps.label = pyglet.text.Label(
            anchor_x='right', anchor_y='top', x=self.window.width, y=self.window.height)

        self.coords = pyglet.text.Label(anchor_x='left', anchor_y='top', x=0, y=self.window.height)

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
        for g in ghost_seq:
            g.anchor_x = g.width / 2
            g.anchor_y = g.width / 2
        self.ghost = [pyglet.sprite.Sprite(img=g, subpixel=True) for g in ghost_seq]
        pyglet.clock.schedule_interval(self.update, 1/240)
    
    def update(self, dt):
        if self.joystick:
            self.state.update(dt, self.joystick.x, self.joystick.y)
        else:
            self.state.update(dt, None, None)
    
    def draw_dead(self):
        self.window.clear()
        label = pyglet.text.Label(text='You are dead',
            anchor_x='center', anchor_y='center', x=self.window.width/2, y=self.window.height/2)
        label.draw()

    def on_draw(self):
        if self.state.dead:
            self.draw_dead()
            return

        self.window.clear()

        cx, cy = self.state.ghost_box.center
        self.viewport.update(cx, cy)

        coords = []
        colors = []
        for box in self.state.boxes:
            x0, y0 = self.viewport.transform(box.x0, box.y0)
            x1, y1 = self.viewport.transform(box.x1, box.y1)
            coords.extend((x0, y0,  x1, y0,  x1, y1,  x0, y1))
            colors.extend([128] * 12)

        pyglet.graphics.draw(4 * len(self.state.boxes), pyglet.gl.GL_QUADS,
                             ('v2f', coords), ('c3B', colors))

        # # Drawing the border around the ghost
        # x0t, y0t = self.viewport.transform(self.state.ghost_box.x0, self.state.ghost_box.y0)
        # x1t, y1t = self.viewport.transform(self.state.ghost_box.x1, self.state.ghost_box.y1)
        # pyglet.graphics.draw(
        #     4, pyglet.gl.GL_LINE_LOOP,
        #     ('v2f', (x0t, y0t,  x1t, y0t,  x1t, y1t,  x0t, y1t)),
        #     ('c3B', [255, 0, 0, 255, 0, 0, 255, 0, 0, 255, 0, 0]))

        ghost_center = self.state.ghost_box.center
        gtx, gty = self.viewport.transform(ghost_center[0], ghost_center[1])
        ghost = self.ghost[self.state.direction]
        ghost.update(x=gtx, y=gty, rotation=self.state.rotation,
                     scale=self.viewport.scale / 16)
        ghost.draw()

        self.coords.text = '({:.2f}, {:.2f})'.format(*self.state.ghost_box.center)
        self.coords.draw()

        self.fps.draw()

    def on_key_press(self, symbol, modifiers):
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
