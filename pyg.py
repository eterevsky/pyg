import math
import pyglet
from pyglet import gl
from pyglet.window import key
import time


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
        if hasattr(other, 'x0'):
            return (self.x0 <= other.x0 and self.y0 <= other.y0 and
                    other.x1 <= self.x1 and other.y1 <= self.y1)
        else:
            return self.x0 <= other[0] <= self.x1 and self.y0 <= other[1] <= self.y1


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


class Jump(object):
    # The amount of time after the player presses jump button, until it has to
    # touch a horizontal surface (bounce).
    JUMP_LAG = 0.1
    # The amount of time for which we accelerate vertically after we've bounced.
    JUMP_DURATION = 0.1
    # Vertical acceleration during the jump duration
    ACCELERATION = 100

    def __init__(self, t):
        self.press_time = t
        self.bounce_time = None
    
    def bounce(self, t):
        if t - self.press_time < self.JUMP_LAG and self.bounce_time is None:
            self.bounce_time = t
    
    @property
    def bounced(self):
        return self.bounce_time is not None
    
    def vert_acc(self, t):
        if self.bounce_time is None or t - self.bounce_time > self.JUMP_DURATION:
            return 0
        else:
            return self.ACCELERATION


class State(object):
    """The state of the game world."""

    def __init__(self):
        self.ghost_box = BoundingBox(0, 0, 0.8, 0.8)
        self.boxes = [
            BoundingBox(-100, -100, 7, 0),
            BoundingBox(9, -100, 100, 0),
            BoundingBox(2, 0, 3, 1),
            BoundingBox(4, 0, 6, 2),
        ]
        for x in range(10):
            for y in range(3):
                self.boxes.append(BoundingBox(2.5*x + (y % 2) + 12,
                                              2.5*y + 1,
                                              2.5*x + (y % 2) + 13,
                                              2.5*y + 2))

        self.goal = BoundingBox(40, 2, 42, 4)

        # If the ghost goes outside this space, it dies.
        self.level_box = BoundingBox(-100, -100, 100, 100)
        self.vx = 0
        self.vy = 0
        self.player_acc = 0
        self.direction = 0
        self.dead = False
        self.won = False

        self.jump_params = None

    @property
    def rotation(self):
        return 5 * math.sin((time.time() % 2) * math.pi)
    
    def accelerate(self, dir):
        self.player_acc += dir

    def jump(self, start):
        """Initiate or finish the jump"""
        self.jump_params = Jump(time.time()) if start else None

    def update(self, dt, acc_x, acc_y):
        if self.dead: return 'dead'
        if self.won: return 'win'

        t = time.time()

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

        ay = -15
        if self.jump_params is not None:
            if not self.jump_params.bounced:
                for box in self.boxes:
                    if self.ghost_box.overlaps_x(box) and 0 <= self.ghost_box.y0 - box.y1 < 0.1:
                        self.jump_params.bounce(t)
            ay += self.jump_params.vert_acc(t)
        self.vy += ay * dt

        self.ghost_box, self.vx, self.vy = move_and_collide(
            self.ghost_box, self.vx, self.vy, dt, self.boxes, 0)
        
        if not self.level_box.contains(self.ghost_box):
            self.dead = True
            return 'dead'
        
        if self.goal.contains(self.ghost_box):
            self.won = True
            return 'win'
        
        return 'normal'


class Viewport(object):
    """Maintain the transform world -> screen so that 

    - viewport in the world has dimentions of roughly 16x9
    - main character is in the screen
    """

    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1

    def update(self, x, y, w, h):
        """Update the viewport transformation.

        Args:
            x, y: coordinates of the tracked object
            w, h: width and height of the window/screen
        """
        old = (self.offset_x, self.offset_y)
        self.scale = h / 9
        scaled_width = w / self.scale
        if x < self.offset_x + 3 - (16 - scaled_width) / 2:
            self.offset_x = x - 3 + (16 - scaled_width) / 2
        elif x > self.offset_x + 13 - (16 - scaled_width) / 2:
            self.offset_x = x - 13 + (16 - scaled_width) / 2
        if y < self.offset_y + 1:
            self.offset_y = y - 1
        elif y > self.offset_y + 8:
            self.offset_y = y - 8
    
    def transform(self, x, y):
        return (x - self.offset_x) * self.scale, (y - self.offset_y) * self.scale


class View(object):
    """An interface to render one of the screens in the game.

    This class if just for documentation purposes, should not be initiated directly.
    """

    NAME = 'default'

    def activate(self, state, window):
        """When called, tells the view, that it is the current view now."""
        pass
    
    def draw(self, state, window):
        """Renders the screen. Has to be overriden."""
        raise NotImplementedError()

    def on_key_press(self, state, symbol, modifiers):
        """Called on key press event. The view is responsible for passing the event to the state."""
        pass
    
    def on_key_release(self, state, symbol, modifiers):
        """Called on key release event. The view is responsible for passing the event to the state."""
        pass

    def on_joybutton_press(self, state, joystick, button):
        pass

    def on_joybutton_release(self, state, joystick, button):
        pass


class NoopView(View):
    NAME = 'noop'
    
    def draw(self, state, window):
        pass


class DeadView(View):
    NAME = 'dead'

    def draw(self, state, window):
        window.clear()
        label = pyglet.text.Label(text='You are dead',
            anchor_x='center', anchor_y='center', x=window.width/2, y=window.height/2)
        label.draw()
    

class WinView(View):
    NAME = 'win'

    def draw(self, state, window):
        window.clear()
        label = pyglet.text.Label(text='You won!',
            anchor_x='center', anchor_y='center', x=window.width/2, y=window.height/2)
        label.draw()
    

class NormalView(View):
    """Main loop and interface with Pyglet."""

    NAME = 'normal'

    def __init__(self):
        self.viewport = Viewport()

        ghost_img = pyglet.resource.image('res/ghost.png')
        ghost_seq = pyglet.image.ImageGrid(ghost_img, 1, 2)
        for g in ghost_seq:
            g.anchor_x = g.width / 2
            g.anchor_y = g.width / 2
        self.ghost = [pyglet.sprite.Sprite(img=g, subpixel=True) for g in ghost_seq]

        self.coords = pyglet.text.Label(anchor_x='left', anchor_y='top')
    
    def activate(self, state, window):
        self.coords = pyglet.text.Label(anchor_x='left', anchor_y='top', x=0, y=window.height)

    def draw(self, state, window):
        window.clear()

        cx, cy = state.ghost_box.center
        self.viewport.update(cx, cy, window.width, window.height)

        coords = []
        colors = []
        for box in state.boxes:
            x0, y0 = self.viewport.transform(box.x0, box.y0)
            x1, y1 = self.viewport.transform(box.x1, box.y1)
            coords.extend((x0, y0,  x1, y0,  x1, y1,  x0, y1))
            colors.extend([128] * 12)
        
        x0, y0 = self.viewport.transform(state.goal.x0, state.goal.y0)
        x1, y1 = self.viewport.transform(state.goal.x1, state.goal.y1)
        coords.extend((x0, y0,  x1, y0,  x1, y1,  x0, y1))
        colors.extend([0, 128, 0] * 4)

        pyglet.graphics.draw(int(len(coords) / 2), pyglet.gl.GL_QUADS,
                             ('v2f', coords), ('c3B', colors))

        # # Drawing the border around the ghost
        # x0t, y0t = self.viewport.transform(self.state.ghost_box.x0, self.state.ghost_box.y0)
        # x1t, y1t = self.viewport.transform(self.state.ghost_box.x1, self.state.ghost_box.y1)
        # pyglet.graphics.draw(
        #     4, pyglet.gl.GL_LINE_LOOP,
        #     ('v2f', (x0t, y0t,  x1t, y0t,  x1t, y1t,  x0t, y1t)),
        #     ('c3B', [255, 0, 0, 255, 0, 0, 255, 0, 0, 255, 0, 0]))

        ghost_center = state.ghost_box.center
        gtx, gty = self.viewport.transform(ghost_center[0], ghost_center[1])
        ghost = self.ghost[state.direction]
        ghost.update(x=gtx, y=gty, rotation=state.rotation,
                     scale=self.viewport.scale / 16)
        ghost.draw()

        self.coords.text = '({:.2f}, {:.2f})'.format(*state.ghost_box.center)
        self.coords.draw()

    def on_key_press(self, state, symbol, modifiers):
        if symbol == key.RIGHT:
            state.accelerate(1)
        elif symbol == key.LEFT:
            state.accelerate(-1)
        elif symbol == key.SPACE:
            state.jump(True)

    def on_key_release(self, state, symbol, modifiers):
        if symbol == key.RIGHT:
            state.accelerate(-1)
        elif symbol == key.LEFT:
            state.accelerate(1)
        elif symbol == key.SPACE:
            state.jump(False)

    def on_joybutton_press(self, state, joystick, button):
        if button == 0:
            state.jump(True)

    def on_joybutton_release(self, state, joystick, button):
        if button == 0:
            state.jump(False)


class Manager(object):
    def __init__(self, state):
        self.state = state
        self.window = pyglet.window.Window(
            config=gl.Config(double_buffer=True), fullscreen=False)

        self.joystick = None
        joysticks = pyglet.input.get_joysticks()
        if joysticks:
            self.joystick = joysticks[0]
            print('Found joystick', self.joystick)
            self.joystick.open()
            self.joystick.push_handlers(self)

        self.views = {}
        self.add_view(NoopView())
        self.set_active_view(NoopView.NAME)
    
        self.fps = pyglet.window.FPSDisplay(self.window)
        self.fps.label = pyglet.text.Label(
            anchor_x='right', anchor_y='top', x=self.window.width, y=self.window.height)

        pyglet.clock.schedule_interval(self.update, 1/240)
        self.window.push_handlers(self)

    def add_view(self, view):
        self.views[view.NAME] = view
    
    def set_active_view(self, view_name):
        self.active_view = self.views[view_name]
        self.active_view.activate(self.state, self.window)

    def on_resize(self, width, height):
        self.window.set_exclusive_mouse(self.window.fullscreen)
        self.window.set_mouse_visible(not self.window.fullscreen)
        self.active_view.activate(self.state, self.window)
        self.fps.label = pyglet.text.Label(
            anchor_x='right', anchor_y='top', x=self.window.width, y=self.window.height)

    def on_draw(self):
        self.active_view.draw(self.state, self.window)
        self.fps.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.F:
            self.window.set_fullscreen(not self.window.fullscreen)
        else:
            self.active_view.on_key_press(self.state, symbol, modifiers)

    def on_key_release(self, symbol, modifiers):
        self.active_view.on_key_release(self.state, symbol, modifiers)

    def on_joybutton_press(self, joystick, button):
        self.active_view.on_joybutton_press(self.state, joystick, button)

    def on_joybutton_release(self, joystick, button):
        self.active_view.on_joybutton_release(self.state, joystick, button)

    def update(self, dt):
        if self.joystick:
            x, y = self.joystick.x, self.joystick.y
        else:
            x, y = None, None 

        new_view = self.state.update(dt, x, y)
        if new_view != self.active_view.NAME:
            self.set_active_view(new_view)    
    

def main():
    state = State()
    manager = Manager(state)
    manager.add_view(NormalView())
    manager.add_view(DeadView())
    manager.add_view(WinView())
    manager.set_active_view(NormalView.NAME)
    pyglet.app.run()


if __name__ == '__main__':
    main()
