#!/usr/bin/env python
# coding: utf

import pygame
import random
import math
import itertools
import numpy as np

SIZE = 640, 480

def intn(*arg):
    return map(int,arg)

def Init(sz):
    '''Turn PyGame on'''
    global screen, screenrect
    pygame.init()
    screen = pygame.display.set_mode(sz)
    screenrect = screen.get_rect()

class GameMode:
    '''Basic game mode class'''
    def __init__(self):
        self.background = pygame.Color("black")

    def Events(self,event):
        '''Event parser'''
        pass

    def Draw(self, screen):
        screen.fill(self.background)

    def Logic(self, screen):
        '''What to calculate'''
        pass

    def Leave(self):
        '''What to do when leaving this mode'''
        pass

    def Init(self):
        '''What to do when entering this mode'''
        pass

class Ball:
    '''Simple ball class'''
    def __init__(self, filename, pos = (0.0, 0.0), speed = (0.0, 0.0)):
        '''Create a ball from image'''
        self.fname = filename
        self.surface = pygame.image.load(filename)
        self.rect = self.surface.get_rect()
        self.speed = speed
        self.pos = pos
        self.newpos = pos
        self.active = True
        self.gravity = 0.7
        self.elasticity = 0.95
        self.radius = self.rect.height / 2

    def draw(self, surface):
        surface.blit(self.surface, self.rect)

    def action(self):
        '''Proceed some action'''
        if self.active:
            self.pos = self.pos[0]+self.speed[0], self.pos[1]+self.speed[1]

    def logic(self, surface):
        x,y = self.pos
        dx, dy = self.speed
        if x < self.rect.width/2:
            x = self.rect.width/2
            dx = -dx * self.elasticity
        elif x > surface.get_width() - self.rect.width/2:
            x = surface.get_width() - self.rect.width/2
            dx = -dx * self.elasticity
        if y < self.rect.height/2:
            y = self.rect.height/2
            dy = -dy * self.elasticity
        elif y > surface.get_height() - self.rect.height/2:
            y = surface.get_height() - self.rect.height/2
            dy = -dy * self.elasticity
        self.pos = x,y
        self.speed = dx, dy + self.gravity
        self.rect.center = intn(*self.pos)


class RotatingBall(Ball):
    """ Rotating ball """
    def __init__(self, filename, pos = (0.0, 0.0), speed = (0.0, 0.0), speed_angular = 0.0, scale = 1.0):
        """
        Rotating ball
        :param filename: path to file with sprite
        :param pos: initial position
        :param speed: initial speed
        :param speed_angular: initial angular speed degrees per frame
        :return:
        """
        Ball.__init__(self, filename, pos, speed)
        self.scale = scale
        self.speed_angular = speed_angular
        self.original_surface = self.surface
        self.angle = 0
        self.radius *= scale

    def logic(self, surface):
        if self.active:
            self.angle = RotatingBall.limit(self.angle + self.speed_angular, 360)
            self.surface = pygame.transform.rotozoom(self.original_surface, self.angle, self.scale)
            self.rect = self.surface.get_rect()
        Ball.logic(self, surface)

    @staticmethod
    def limit(value, limit):
        """
        Normalize value to range [0, limit)
        :param value: value to normalize
        :param limit: positive limit
        :return: value in range [0, limit)
        """
        return value - limit * int(value / limit)


class Universe:
    '''Game universe'''

    def __init__(self, msec, tickevent = pygame.USEREVENT):
        '''Run a universe with msec tick'''
        self.msec = msec
        self.tickevent = tickevent

    def Start(self):
        '''Start running'''
        pygame.time.set_timer(self.tickevent, self.msec)

    def Finish(self):
        '''Shut down an universe'''
        pygame.time.set_timer(self.tickevent, 0)

class GameWithObjects(GameMode):

    def __init__(self, objects=[]):
        GameMode.__init__(self)
        self.objects = objects

    def locate(self, pos):
        return [obj for obj in self.objects if obj.rect.collidepoint(pos)]

    def Events(self, event):
        GameMode.Events(self, event)
        if event.type == Game.tickevent:
            for obj in self.objects:
                obj.action()

    def Logic(self, surface):
        GameMode.Logic(self, surface)
        for obj in self.objects:
            obj.logic(surface)

        active_objects = filter(lambda obj: obj.active, self.objects)
        for pair in itertools.combinations(active_objects, 2):
            collision = self.collision_detect(*pair)
            if collision:
                pair[0].pos = collision['position_a']
                pair[1].pos = collision['position_b']
                pair[0].active = pair[1].active = False


    def Draw(self, surface):
        GameMode.Draw(self, surface)
        for obj in self.objects:
            obj.draw(surface)

    @staticmethod
    def collision_detect(ball_a, ball_b):
        a = np.array(ball_a.pos)
        b = np.array(ball_b.pos)
        va = np.array(ball_a.speed)
        vb = np.array(ball_b.speed)
        v = va - vb
        c = b - a
        v_norm = np.linalg.norm(v)
        if np.linalg.norm(c) > (v_norm + ball_a.radius + ball_b.radius):
            # за текущий кадр шары не долетят друг до друга
            return None
        if np.dot(c, v) <= 0:
            # мячи удаляются друг от друга
            return None
        n = v / v_norm
        # расстояние от ball_a до точки на векторе движения, наиболее близкой к ball_b
        d = np.dot(n, c)
        f_square = np.linalg.norm(c)**2 - d**2
        smallest_dist_square = (ball_a.radius + ball_b.radius) ** 2
        if f_square > smallest_dist_square:
            # шары пролетят мимо
            return None
        # расстояние по вектору v от ball_a до точки соударения
        distance = d - math.sqrt(smallest_dist_square - f_square)
        #
        delta = distance / v_norm
        return {
            'position_a': tuple(a + va * delta),
            'position_b': tuple(b + vb * delta)
        }


class GameWithDnD(GameWithObjects):

    def __init__(self, *argp, **argn):
        GameWithObjects.__init__(self, *argp, **argn)
        self.oldpos = 0,0
        self.drag = None

    def Events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            click = self.locate(event.pos)
            if click:
                self.drag = click[0]
                self.drag.active = False
                self.oldpos = event.pos
        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
                if self.drag:
                    self.drag.pos = event.pos
                    self.drag.speed = event.rel
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag:
            self.drag.active = True
            self.drag = None
        GameWithObjects.Events(self, event)

Init(SIZE)
Game = Universe(150)

Run = GameWithDnD()
for i in xrange(2):
    x, y = random.randrange(screenrect.w), random.randrange(screenrect.h)
    dx, dy = 1+random.random()*5, 1+random.random()*5
    angular = 5 * (random.random() - 0.5)
    scale = random.random() + 0.5
    Run.objects.append(RotatingBall("ball.gif",(x,y),(dx,dy), speed_angular=angular, scale=scale))

Game.Start()
Run.Init()
again = True
while again:
    event = pygame.event.wait()
    if event.type == pygame.QUIT:
        again = False
    Run.Events(event)
    Run.Logic(screen)
    Run.Draw(screen)
    pygame.display.flip()
Game.Finish()
pygame.quit()
