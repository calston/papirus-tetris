#!/usr/bin/python

import os
import sys
import time
import random

from PIL import Image
from PIL import ImageDraw
from papirus import Papirus
import RPi.GPIO as GPIO

SW = [21, 16, 20, 19, 26]

GPIO.setmode(GPIO.BCM)

for io in SW:
    GPIO.setup(io, GPIO.IN)

BLOCKS = [
    ((0, 1),
     (1, 1),
     (0, 1)),

    ((0, 1),
     (1, 1),
     (1, 0)),
           
    ((1, 0),
     (1, 1),
     (0, 1)),

    ((1, ),
     (1, ),
     (1, ),
     (1, )),

    ((1, 1),
     (1, 1)),

    ((1, 1),
     (1, 0),
     (1, 0)),

    ((1, 1),
     (0, 1),
     (0, 1)),
]

class Block(object):
    def __init__(self, pattern):
        self.pattern = pattern

        self.position = [0, 4]

    def moveDown(self):
        maxx = len(self.pattern)
        if (self.position[0] + maxx < 21):
            self.position[0] += 1

    def moveRight(self):
        if self.position[1] >= 1:
            self.position[1] -= 1

    def moveLeft(self):
        if self.position[1] + len(self.pattern[0]) < 10:
            self.position[1] += 1

    def rotateLeft(self):
        maxy = len(self.pattern[0])
        maxx = len(self.pattern)
        newmatrix = [[0 for i in range(maxx)] for i in range(maxy)]
        for x in range(maxx):
            for y in range(maxy):
                newmatrix[maxy-1-y][x] = self.pattern[x][y]
            
        # Shift the piece away from the edge
        if (len(newmatrix[0]) + self.position[1]) > 10:
            self.position[1] = 10 - len(newmatrix[0])

        self.pattern = newmatrix

    def rotateRight(self):
        maxy = len(self.pattern[0])
        maxx = len(self.pattern)
        newmatrix = [[0 for i in range(maxx)] for i in range(maxy)]
        for x in range(maxx):
            for y in range(maxy):
                newmatrix[y][maxx-1-x] = self.pattern[x][y]
        
        if (len(newmatrix[0]) + self.position[1]) > 10:
            self.position[1] = 10 - len(newmatrix[0])

        self.pattern = newmatrix

class Game(object):
    def __init__(self):
        self.screen = Papirus()

        self.screen.clear()

        self.image = Image.new('1', self.screen.size, 1)
        self.canvas = ImageDraw.Draw(self.image)

        self.run = True
        self.speed = 0.01
        self.down = 0

        self.field = [[0 for i in range(10)] for i in range(21)]
        
        self.getBlock()

    def getBlock(self):
        self.currentBlock = Block(random.choice(BLOCKS))
        #self.currentBlock = Block(BLOCKS[0])

    def disp(self):
        self.screen.display(self.image)
        self.screen.partial_update()

    def draw(self):
        for x, row in enumerate(self.field):
            for y, b in enumerate(row):
                cord = (x*9, y*9)
                cord2 = (cord[0] + 9, cord[1] + 9)
                if b:
                    self.canvas.rectangle((cord, cord2), fill=0, outline=1)
                else:
                    self.canvas.rectangle((cord, cord2), fill=1, outline=1)

        self.disp()

    def eraseBlock(self):
        ax, ay = self.currentBlock.position
        for x, row in enumerate(self.currentBlock.pattern):
            for y, v in enumerate(row):
                if v:
                    self.field[ax + x][ay + y] = 0

    def drawBlock(self):
        ax, ay = self.currentBlock.position
        for x, row in enumerate(self.currentBlock.pattern):
            for y, v in enumerate(row):
                if v:
                    self.field[ax + x][ay + y] = 1

    def clip(self):
        ax, ay = self.currentBlock.position
        
        maxy = len(self.currentBlock.pattern[0])
        maxx = len(self.currentBlock.pattern)

        if (maxx + ax) >= len(self.field):
            return True

        extents = [-1 for i in range(maxy)]

        for i in reversed(range(maxx)):
            for j in range(maxy):
                if (self.currentBlock.pattern[i][j] == 1) and (extents[j] == -1):
                    extents[j] = i

        for y, x in enumerate(extents):
            if self.field[ax + x + 1][ay + y] == 1:
                return True

        return False

    def checkField(self):
        newfield = []
        for x, row in enumerate(self.field):
            if sum(row) != len(row):
                newfield.append(row)

        self.field = [[0 for i in range(10)] for i in range(21 - len(newfield))]
        self.field.extend(newfield)

    def clipRight(self):
        ax, ay = self.currentBlock.position
        
        maxx = len(self.currentBlock.pattern)
        maxy = len(self.currentBlock.pattern[0])

        if ay > 0:
            for i, row in enumerate(self.currentBlock.pattern):
                try:
                    maxr = row.index(1)
                    if row[maxr] and self.field[ax + i][ay + maxr - 1]:
                        return True
                except ValueError as e:
                    pass
        else:
            return True

    def clipLeft(self):
        ax, ay = self.currentBlock.position
        
        maxx = len(self.currentBlock.pattern)
        maxy = len(self.currentBlock.pattern[0])


        if (ay + maxy) < 10:
            for i, row in enumerate(self.currentBlock.pattern):
                try:
                    minr = len(row) - 1 - row[::-1].index(1)

                    if row[minr] and self.field[ax + i][ay + minr + 1]:
                        return True
                except ValueError as e:
                    pass
        else:
            return True

    def tick(self):

        redraw = False
        if GPIO.input(SW[0]) == False:
            if not self.clipRight():
                self.eraseBlock()
                self.currentBlock.moveRight()
                self.drawBlock()
                redraw = True

        if GPIO.input(SW[1]) == False:
            if not self.clipLeft():
                self.eraseBlock()
                self.currentBlock.moveLeft()
                self.drawBlock()
                redraw = True

        if GPIO.input(SW[2]) == False:
            self.eraseBlock()
            self.currentBlock.rotateLeft()
            self.drawBlock()
            redraw = True

        if GPIO.input(SW[3]) == False:
            self.eraseBlock()
            self.currentBlock.rotateRight()
            self.drawBlock()
            redraw = True

        if (self.down > 4):
            self.down = 0
            clipped = self.clip()
            if not clipped:
                self.eraseBlock()
                self.currentBlock.moveDown()
                self.drawBlock()
                redraw = True
            else:
                self.checkField()
                self.getBlock()
                redraw = True
        else:
            self.down += 1

        if redraw:
            self.draw()
    
    def loop(self):
        while self.run:
            time.sleep(self.speed)
            self.tick()

game = Game()

game.draw()
game.loop()
