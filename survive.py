import math
import random
import sys
import time
from typing import Any, List, Sequence

import pygame as pg
from pygame.rect import Rect
from pygame.sprite import AbstractGroup, Sprite
from pygame.surface import Surface


WIDTH = 1600  # ゲームウィンドウの幅
HEIGHT = 900  # ゲームウィンドウの高さ


class Camera():
    def __init__(self, center_pos: list[float] = [0, 0]) -> None:
        self.center_pos = center_pos


class Group_custom(pg.sprite.Group):
    def __init__(self, camera: Camera, *sprites: Sprite | Sequence[Sprite]) -> None:
        super().__init__(*sprites)
        self.camera = camera

    def draw(self, surface: Surface) -> List[Rect]:
        for sprite in self.sprites():
            sprite.rect.move_ip(
                -self.camera.center_pos[0] + WIDTH / 2,
                -self.camera.center_pos[1] + HEIGHT / 2
            )

        rst = super().draw(surface)

        for sprite in self.sprites():
            sprite.rect.move_ip(
                self.camera.center_pos[0] - WIDTH / 2,
                self.camera.center_pos[1] - HEIGHT / 2
            )

        return rst


class Character(pg.sprite.Sprite):
    def __init__(self, hp: int, max_invincible_tick=0) -> None:
        super().__init__()
        self.hp = hp
        self.max_invincible_tick = max_invincible_tick
        self.invincible_tmr = -1
        self.imgs: dict[int, list[Surface, (int | None)]] = {}

    def give_damage(self, damage: int) -> int:
        if self.invincible_tmr <= 0:
            self.hp -= damage
            self.invincible_tmr = self.max_invincible_tick
            self.damaged()
        if self.hp <= 0:
            self.kill()
        return self.hp

    def damaged(self):
        pass

    def update(self):
        self.invincible_tmr = max(self.invincible_tmr - 1, -1)
        if len(self.imgs) > 0:
            idx = max(self.imgs)
            self.image = self.imgs[idx][0]
            if self.imgs[idx][1] != None:
                if self.imgs[idx][1] < 0:
                    del self.imgs[idx]
                else:
                    self.imgs[idx][1] -= 1


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


def calc_norm(org: pg.Rect, dst: pg.Rect) -> float:
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    return math.sqrt(x_diff ** 2 + y_diff ** 2)


class Bird(Character):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """

    IMAGE_SCALE = 1.2

    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: list[int, int], hp=50, max_invincible_tick=50):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル 
        """
        super().__init__(hp, max_invincible_tick=max_invincible_tick)
        img0 = pg.transform.rotozoom(
            pg.image.load(f"ex04/fig/{num}.png"), 0, self.IMAGE_SCALE)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.move_imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (1, 0)
        self.imgs[0] = [self.move_imgs[self.dire], None]
        self.image = self.imgs[0][0]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, priority: int, life_tick: int | None = None):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """

        self.imgs[priority] = [
            pg.transform.rotozoom(
                pg.image.load(f"ex04/fig/{num}.png"), 0, self.IMAGE_SCALE),
            life_tick
        ]

    def damaged(self):
        super().damaged()
        self.change_img(8, 5, 20)

    def update(self, key_lst: list[bool]):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        super().update()
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                self.rect.move_ip(+self.speed*mv[0], +self.speed*mv[1])
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.imgs[0][0] = self.move_imgs[self.dire]

    def get_direction(self) -> tuple[int, int]:
        return self.dire

    def kill(self) -> None:
        pass


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    MAX_LIFE_TICK = 250

    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.get_direction()
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.Surface((20, 20))
        self.rect = self.image.get_rect()
        pg.draw.rect(self.image, (255, 0, 0), self.rect)
        self.image = pg.transform.rotozoom(self.image, angle, 1)

        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 20

        self.life_tmr = 0

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if self.life_tmr > self.MAX_LIFE_TICK:
            self.kill()
        self.life_tmr += 1


class Enemy(Character):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"EX04/fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self, hp: int, spawn_point: list[int, int], chase_target: Character):
        super().__init__(hp)
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = spawn_point
        self.speed = 5
        self.chase_target = chase_target

    def update(self):
        super().update()

        if calc_norm(self.rect, self.chase_target.rect) < 50:
            return
        dir = list(calc_orientation(self.rect, self.chase_target.rect))
        self.rect.move_ip(dir[0] * self.speed, dir[1] * self.speed)


class Background(pg.sprite.Sprite):
    def __init__(self, camera: Camera, offset: tuple[int, int]) -> None:
        super().__init__()
        self.image = pg.image.load("ex05/fig/background.png")
        self.rect = self.image.get_rect()
        self.rect.topleft = (0, 0)
        self.offset = offset
        self.camera = camera

    def update(self) -> None:
        super().update()
        x_offset = self.offset[0]
        if self.camera.center_pos[0] != 0:
            x_offset += self.camera.center_pos[0] // self.rect.width
        y_offset = self.offset[1]
        if self.camera.center_pos[1] != 0:
            y_offset += self.camera.center_pos[1] // self.rect.height
        self.rect.topleft = (x_offset * self.rect.width,
                             y_offset * self.rect.height)


def main():
    pg.display.set_caption("サバイブ")
    screen = pg.display.set_mode((WIDTH, HEIGHT))

    camera = Camera([0, 0])
    background = Group_custom(camera)
    for i in range(-2, 3):
        for j in range(-1, 2):
            background.add(Background(camera, (i, j)))
    bird = Bird(3, [0, 0])
    bird_group = Group_custom(camera, bird)
    beams = Group_custom(camera)
    emys = Group_custom(camera)

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0

        if tmr % 5 == 0:
            beams.add(Beam(bird))

        if tmr % 30 == 0:
            angle = random.randint(0, 360)
            spawn_dir = [
                math.cos(math.radians(angle)),
                -math.sin(math.radians(angle))
            ]
            emys.add(Enemy(
                20,
                [camera.center_pos[0] + (spawn_dir[0] * 1000),
                     camera.center_pos[1] + (spawn_dir[1] * 1000)],
                bird)
            )

        for enemy in pg.sprite.groupcollide(emys, beams, False, True).keys():
            enemy.give_damage(10)

        for _ in pg.sprite.spritecollide(bird, emys, False):
            bird.give_damage(10)

        background.update()
        background.draw(screen)

        if bird.hp <= 0:
            bird.change_img(8, 10, 250)
            bird.update(key_lst)
            bird_group.draw(screen)
            pg.display.update()
            time.sleep(2)
            return

        bird.update(key_lst)
        beams.update()
        emys.update()

        camera.center_pos[0] = bird.rect.centerx
        camera.center_pos[1] = bird.rect.centery
        
        bird_group.draw(screen)
        beams.draw(screen)
        emys.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
