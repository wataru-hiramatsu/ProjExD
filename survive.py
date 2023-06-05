import math
import random
import sys
import time
from typing import List, Sequence, cast

import pygame as pg
from pygame.rect import Rect
from pygame.sprite import Sprite
from pygame.surface import Surface

pg.init()
pg.mixer.init()

WIDTH = 1600  # ゲームウィンドウの幅
HEIGHT = 900  # ゲームウィンドウの高さ

def clamp(v, small, large):
    return max(small, min(v, large))

class Camera():
    """
    カメラに関するクラス
    """

    active_camera: "Camera" = None

    def __init__(self, screen: Surface, targetCharacter: "Character", is_acrive_now=True) -> None:
        """
        カメラを生成する関数
        引数1: 描画先のSurface
        引数2: カメラのスポーン位置（カメラ中心位置が原点）
        """
        self.screen = screen
        self.center_pos = [0, 0]
        self.targetCharacter = targetCharacter
        if is_acrive_now:
            self.__class__.active_camera = self
    
    def update(self, delta_time: float) -> None:
        """
        カメラの位置を更新する関数
        引数1: 前のフレームからの経過時間
        """
        self.center_pos = list(self.targetCharacter.rect.center)
        self.center_pos[0] = clamp(self.center_pos[0], -MoveArea.width / 2 + self.screen.get_width() / 2, MoveArea.width / 2 - self.screen.get_width() / 2)
        self.center_pos[1] = clamp(self.center_pos[1], -MoveArea.height / 2 + self.screen.get_height() / 2, MoveArea.height / 2 - self.screen.get_height() / 2)

    def is_in_camera(self, pos: tuple[int, int]) -> tuple[bool, bool]:
        return (
            self.center_pos[0] - self.screen.get_width() / 2 <= pos[0] <= self.center_pos[0] + self.screen.get_width() / 2,
            self.center_pos[1] - self.screen.get_height() / 2 <= pos[1] <= self.center_pos[1] + self.screen.get_height() / 2
        )


class Group_support_camera(pg.sprite.Group):
    """
    Surfaceをカメラ位置に同期して描画するためのグループクラス
    """
    def __init__(self, *sprites: Sprite | Sequence[Sprite]) -> None:
        super().__init__(*sprites)

    def draw(self, surface: Surface) -> List[Rect]:
        """
        グループ内にあるSpriteをカメラ位置に合わせて描画する関数
        引数1: 描画先のSurface
        """
        camera = Camera.active_camera
        # カメラ位置だけSprite達をずらす
        for sprite in self.sprites():
            sprite.rect.move_ip(
                -camera.center_pos[0] + camera.screen.get_width() / 2,
                -camera.center_pos[1] + camera.screen.get_height() / 2
            )

        # 描画
        rst = super().draw(surface)

        # 動かしたSprite達の位置を戻す
        for sprite in self.sprites():
            sprite.rect.move_ip(
                camera.center_pos[0] - camera.screen.get_width() / 2,
                camera.center_pos[1] - camera.screen.get_height() / 2
            )

        return rst
    
class MoveArea():
    width: int = 4000
    height: int = 3000
    
    @classmethod
    def is_in_area(cls, pos: tuple[int, int]) -> tuple[bool, bool]:
        return (
            -cls.width / 2 <= pos[0] <= cls.width / 2,
            -cls.height / 2 <= pos[1] <= cls.height / 2
        )


class Character(pg.sprite.Sprite):
    """
    PlayerやEnemyなどの基底クラス
    """
    def __init__(self, image: Surface, position: tuple[int, int], hp: int, max_invincible_sec=0) -> None:
        """
        キャラクタSurfaceを生成
        引数1: キャラの基本画像
        引数2: スポーン位置
        引数3: 体力
        引数4: ダメージを受けた際に無敵になるフレーム数（任意）
        """
        super().__init__()
        self.max_hp = hp
        self.hp = hp
        self.max_invincible_tick = max_invincible_sec
        self.invincible_tmr = -1
        self._imgs: dict[int, list[Surface, (int | None)]] = {}
        self.set_image(image, 0)
        self.rect = image.get_rect()
        self.rect.center = position
    
    def set_image(self, image: Surface, priority: int, valid_time: int | None = None):
        """
        キャラの画像を切り替える関数
        引数1: 画像
        引数2: 画像の優先度。数値が高いほど優先して表示される。（ダメージを受けた際に数秒間だけ基本画像から変更したいときに便利）
        引数3: 画像を描画する期間（Noneで無期限になります）
        """
        self._imgs[priority] = [image, valid_time]

    def give_damage(self, damage: int) -> int:
        """
        キャラにダメージを与える関数
        引数1: ダメージ
        戻り値: 減った後のHP
        """
        if self.invincible_tmr <= 0:
            self.hp -= damage
            self.invincible_tmr = self.max_invincible_tick
            self.damaged()
        if self.hp <= 0:
            self.kill()
        return self.hp

    def damaged(self):
        """
        ダメージを与えられた際に呼ばれる関数。
        """
        # カメラからの距離によって音量を変える
        volume_range = 1500
        volume = max((volume_range - calc_norm(self.rect.center, Camera.active_camera.center_pos)) / volume_range, 0)
        if self.hp > 0:
            sound = pg.mixer.Sound("ex05/fig/se_enemy_damage.mp3")
            sound.set_volume(volume)
            sound.play()
        else:
            sound = pg.mixer.Sound("ex05/fig/se_enemy_death.mp3")
            sound.set_volume(volume)
            sound.play()

    def update(self, delta_time: float):
        # 無敵時間を減らす処理
        self.invincible_tmr = max(self.invincible_tmr - delta_time, -1)

        # 表示する画像周りの処理
        if len(self._imgs) > 0:
            # 優先度が最も高い画像を描画
            idx = max(self._imgs)
            self.image = self._imgs[idx][0]
            # 画像の有効時間を減らす処理
            if self._imgs[idx][1] != None:
                if self._imgs[idx][1] < 0:
                    del self._imgs[idx]
                    return
                self._imgs[idx][1] -= delta_time


def calc_orientation(org: tuple[int, int], dst: tuple[int, int]) -> tuple[float, float]:
    """
    orgから見てdstがどこにあるかを計算し方向ベクトルを返す関数
    引数1 org:座標
    引数2 dst:座標
    戻り値:orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst[0] - org[0], dst[1] - org[1]
    norm = math.sqrt(x_diff ** 2 + y_diff ** 2)
    return x_diff / norm, y_diff / norm


def calc_norm(org: pg.Rect, dst: pg.Rect) -> float:
    """
    orgとdstとの間の距離を返す関数
    引数1 org:Rect
    引数2 dst:Rect
    戻り値:距離
    """
    return calc_norm(org.center, dst.center)

def calc_norm(org: tuple[int, int], dst: tuple[int, int]) -> float:
    """
    orgとdstとの間の距離を返す関数
    引数1 org:座標
    引数2 dst:座標
    戻り値:距離
    """
    x_diff, y_diff = dst[0] - org[0], dst[1] - org[1]
    return math.sqrt(x_diff ** 2 + y_diff ** 2)


class Player(Character):
    """
    Playerに関するクラス
    """

    # Playerの画像の表示倍率
    IMAGE_SCALE = 1.2

    delta = {  # 押下キーと移動量の辞書
        pg.K_w: (0, -1),
        pg.K_s: (0, +1),
        pg.K_a: (-1, 0),
        pg.K_d: (+1, 0),
    }

    def __init__(self, xy: list[int, int], effect_group: pg.sprite.Group, hp=50, max_invincible_sec=2):
        """
        Playerを生成
        引数1: スポーン位置
        引数2: hp(任意)
        引数3: ダメージを受けた際の無敵時間（任意）
        """
        img0 = pg.transform.rotozoom(
            pg.image.load(f"ex05/fig/3.png"), 0, self.IMAGE_SCALE)
        img = pg.transform.flip(img0, True, False)
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
        super().__init__(self.move_imgs[self.dire], xy ,hp, max_invincible_sec)
        self.speed = 500
        self.attack_interval = 0.2
        self.attack_number = 1
        effect_group.add(HP_Bar(self))

    def change_img(self, num: int, priority: int, life: int | None = None):
        """
        Player画像を設定する関数
        引数1: num：Player画像ファイル名の番号
        引数2: 画像の優先度
        引数3: 表示する期間（Noneで無期限）
        """
        self.set_image(pg.transform.rotozoom(pg.image.load(f"ex05/fig/{num}.png"), 0, self.IMAGE_SCALE), priority, life)

    def damaged(self):
        """
        Playerがダメージを受けたときに実行される関数
        """
        super().damaged()

        # 数秒間だけ専用画像に切り替える
        self.change_img(8, 5, 2)

    def update(self, key_lst: list[bool], dtime):
        """
        押下キーに応じてPlayerを移動させる
        引数1: key_lst：押下キーの真理値リスト
        """
        super().update(dtime)
        sum_mv = [0, 0]
        for k, mv in Player.delta.items():
            if key_lst[k]:
                move_vec = [self.speed * mv[0] * dtime, self.speed * mv[1] * dtime]
                movable = MoveArea.is_in_area((self.rect.center[0] + move_vec[0], self.rect.center[1] + move_vec[1]))
                if movable[0]:
                    self.rect.move_ip(move_vec[0], 0)
                if movable[1]:
                    self.rect.move_ip(0, move_vec[1])
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.set_image(self.move_imgs[self.dire], 0)

    def get_direction(self) -> tuple[int, int]:
        """
        Playerの向いている向きを返す関数
        戻り値: 方向ベクトル
        """
        return self.dire

    def kill(self) -> None:
        pass


class Bullet(pg.sprite.Sprite):
    """
    弾に関するクラス
    """

    def __init__(self,
                 image: Surface,
                 position: tuple[int, int],
                 direction: tuple[float, float],
                 attackable_group: pg.sprite.Group,
                 speed=500,
                 damage: int=10,
                 life_sec=5,
                 is_fix_rotation_img=False,
                 is_destoroy_when_off_screen=False):
        """
        銃弾Surfaceを生成する
        引数1: スポーン位置
        引数2: 飛ばす方向
        """
        super().__init__()
        self.vx, self.vy = direction
        self.image = image
        if not is_fix_rotation_img:
            angle = math.degrees(math.atan2(-self.vy, self.vx))
            self.image = pg.transform.rotozoom(image, angle, 1)
            self.image.set_colorkey((0,0,0))
        self.rect = self.image.get_rect()
        self.rect.center = position
        self.speed = speed
        self.life_tmr = 0
        self.attackable_group = attackable_group
        self.damage = damage
        self.max_life_sec = life_sec
        self.isdestoroy_when_off_screen = is_destoroy_when_off_screen

    def update(self, dtime: float, score: "Score"):
        """
        銃弾を移動させる
        """
        # 移動
        self.rect.move_ip(self.speed * self.vx * dtime, self.speed * self.vy * dtime)
        in_camera = Camera.active_camera.is_in_camera(self.rect.center)
        is_in_camera = in_camera[0] and in_camera[1]
        if self.life_tmr > self.max_life_sec or (self.isdestoroy_when_off_screen and not is_in_camera):
            self.kill()
        self.life_tmr += dtime

        # 衝突判定
        for damage_target in pg.sprite.spritecollide(self, self.attackable_group, False):
            self.kill()

            damage_target = cast(Character, damage_target)
            damage_target.give_damage(self.damage)
            # TODO: Enemy_Baseに依存させるのは良くないのでIScoreable的なのを作ってそこに依存させる
            if damage_target.hp <= 0 and issubclass(type(damage_target), Enemy_Base):
                score.score_up(damage_target.get_score())


def gen_beams(image: Surface,
              player: Player, 
              target_angle: float, 
              attackable_group: pg.sprite.Group, 
              speed=500,
              damage=10,
              life_sec=5,
              bullet_count=1, 
              angle_range=30) -> list[Bullet]:
    """
    gen_beams関数で，
    ‐30°～+31°の角度の範囲で指定ビーム数の分だけBeamオブジェクトを生成し，
    リストにappendする → リストを返す
    """
    interval_rad = math.radians(angle_range) / (bullet_count - 1) if bullet_count != 1 else 0
    rad_range = interval_rad * (bullet_count - 1) if bullet_count != 0 else 0

    bullets: list[Bullet] = []
    for i in range(bullet_count):
        rad = i * interval_rad - rad_range / 2 + math.radians(target_angle)
        bullets.append(Bullet(image, player.rect.center, (math.cos(rad), math.sin(rad)), attackable_group, speed, damage, life_sec, is_destoroy_when_off_screen=True))
    return bullets

class Enemy_Base(Character):
    def __init__(self,
                 image: Surface,
                 position: tuple[int, int],
                 hp: int,
                 effect_group: pg.sprite.Group,
                 max_invincible_sec=0,
                 score=0) -> None:
        super().__init__(image, position, hp, max_invincible_sec)
        self.effect_group = effect_group
        self._score = score
        self.effect_group.add(HP_Bar(self))
    
    def get_score(self) -> int:
        return self._score


class Enemy(Enemy_Base):
    """
    敵に関するクラス
    """
    # TODO: グループ周りの引数が多すぎるのでなんとかしたい
    # （この規模ならGameManagerクラスを作って、グループ達をそのクラス変数として持たせてどこからもアクセス出来るようにしてもいいかも）
    def __init__(self, spawn_point: list[int, int], attack_target: Character, effect_group:pg.sprite.Group, hp=20, score=30, speed=100):
        """
        敵を生成する関数
        引数3: 攻撃を加える対象
        """
        imgs = [pg.image.load(f"ex05/fig/zonbi{i}.png") for i in range(1, 4)]
        imgs[0] = pg.transform.scale(imgs[0],(random.randint(90,150),random.randint(90,150)))
        imgs[1] = pg.transform.scale(imgs[1],(random.randint(90,150),random.randint(90,150)))
        imgs[2] = pg.transform.scale(imgs[2],(random.randint(90,150),random.randint(90,150)))
        super().__init__(random.choice(imgs), spawn_point, hp, effect_group, score=score)
        self.speed = speed
        self.attack_target = attack_target

    def update(self, dtime):
        """
        敵を移動させる関数
        """
        super().update(dtime)
        # 攻撃対象に近づき過ぎたら止まる（0割り対策）
        if calc_norm(self.rect, self.attack_target.rect) < 50:
            return
        dir = list(calc_orientation(self.rect, self.attack_target.rect))
        self.rect.move_ip(dir[0] * self.speed * dtime, dir[1] * self.speed * dtime)


class BOSS(Enemy_Base):
    """
    ボスに関するクラス
    """
    ATTACK_INTERVAL_SEC = 1.0

    def __init__(self,
                 spawn_point: list[int, int],
                 attack_target: Character,
                 effect_group:pg.sprite.Group,
                 enemy_bullet_group: pg.sprite.Group,
                 hp=50,
                 score=40,
                 speed=100):
        """
        ボスを生成する関数
        引数3: 攻撃を加える対象
        """
        super().__init__((pg.transform.rotozoom((pg.image.load(f"ex05/fig/alien2.png")), 0.0, 3.0)), spawn_point, hp, effect_group, score=score)
        self.speed = speed
        self.attack_target = attack_target
        self.enemy_bullet_group = enemy_bullet_group
        self._attack_interval_tmr = 0.0
        self.bullet_img = pg.transform.rotozoom((pg.image.load("ex05/fig/flame.png")), 0, 0.1)

    def update(self, delta_time: float):
        """
        ボスを移動させる関数
        """
        super().update(delta_time)

        # 攻撃対象に近づき過ぎたら止まる（0割り対策）
        if calc_norm(self.rect, self.attack_target.rect) < 50:
            return
        dir = list(calc_orientation(self.rect, self.attack_target.rect))
        self.rect.move_ip(dir[0] * self.speed * delta_time, dir[1] * self.speed * delta_time)

        # 一定間隔で射撃を行う
        if self._attack_interval_tmr > self.ATTACK_INTERVAL_SEC:
            direction = calc_orientation(self.rect.midbottom, self.attack_target.rect.center)  
            self.enemy_bullet_group.add(Bullet(self.bullet_img, self.rect.midbottom, direction, self.attack_target.groups()[0], is_fix_rotation_img=True))
            self._attack_interval_tmr = 0
        self._attack_interval_tmr += delta_time


class Background(pg.sprite.Sprite):
    """
    背景に関するクラス
    """
    def __init__(self, camera: Camera, offset: tuple[int, int]) -> None:
        """
        背景を生成する関数
        引数1: カメラ
        引数2: 背景のデフォルト生成位置からどれだけずらすか
        """
        super().__init__()
        self.image = pg.image.load("ex05/fig/background.png")
        self.rect = self.image.get_rect()
        self.rect.topleft = (0, 0)
        self.offset = offset
        self.camera = camera

    def update(self) -> None:
        """
        カメラの位置に合わせて背景を動かす関数
        """
        super().update()
        x_offset = self.offset[0]
        if self.camera.center_pos[0] != 0:
            x_offset += self.camera.center_pos[0] // self.rect.width
        y_offset = self.offset[1]
        if self.camera.center_pos[1] != 0:
            y_offset += self.camera.center_pos[1] // self.rect.height
        self.rect.topleft = (x_offset * self.rect.width,
                             y_offset * self.rect.height)


class HP_Bar(pg.sprite.Sprite):
    _BAR_COLOR = (255, 0, 0)
    _BAR_BACKGROUND_COLOR = (0, 0, 0)

    def update_image(self) -> pg.Surface:
        percent = self.target_character.hp / self.target_character.max_hp
        self.image.fill(self._BAR_BACKGROUND_COLOR)
        pg.draw.rect(self.image, self._BAR_COLOR, pg.Rect(0, 0, self.image.get_width() * percent, self.image.get_height()))

    def __init__(self, target_character: Character, width: int=100, height: int=10, offset_y:int=10) -> None:
        super().__init__()
        self.target_character = target_character
        self.image = pg.Surface((width, height))
        self.update_image()
        self.rect = self.image.get_rect()
        self.offset_y = offset_y

        self.rect.midbottom = self.target_character.rect.midtop
        self.rect.y -= offset_y
    
    def update(self, delta_time: float) -> None:
        self.rect.midbottom = self.target_character.rect.midtop
        self.rect.y -= self.offset_y
        self.update_image()

        if self.target_character.hp <= 0:
            self.kill()


class Score:
    """
    倒した敵の数をスコアとして表示するクラス
    敵：30点
    """
    def __init__(self,camera:Camera):
        self.font = pg.font.Font(None, 50)
        self.color = (255, 255, 255)
        self.score = 0
        self.image = self.font.render(f"Score: {self.score}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, camera.screen.get_height() - 50

    def score_up(self, add):
        self.score += add

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.score}", 0, self.color)
        screen.blit(self.image, self.rect)

def get_random_spawn_pos(range: int=-1) -> tuple[int, int]:
    range = Camera.active_camera.screen.get_width() // 2 + 500 if range < 0 else range
    spawn_rad = math.radians(random.randint(0, 360))
    spawn_dir = [math.cos(spawn_rad), -math.sin(spawn_rad)]
    center_pos = Camera.active_camera.center_pos
    return [center_pos[0] + (spawn_dir[0] * range), center_pos[1] + (spawn_dir[1] * range)]

def main():
    max_fps = 60
    dtime = 0 # 前のフレームからどのくらい経ったか
    gameFlag = False

    pg.display.set_caption("サバイブ")
    screen = pg.display.set_mode((1600, 900))

    # 様々な変数の初期化
    effect_group = Group_support_camera()
    player = Player([0, 0], effect_group)
    camera = Camera(screen, player)
    background = Group_support_camera()
    for i in range(-2, 3):
        for j in range(-1, 2):
            background.add(Background(camera, (i, j)))
    player_group = Group_support_camera(player)
    bullets = Group_support_camera()
    enemies = Group_support_camera()
    flame = Group_support_camera()
    clock = pg.time.Clock()
    score = Score(camera)

    clk = 0
    enemy_spawn_interval_sec = 0.5
    enemy_spawn_interval_tmr = 0
    fast_enemy_spawn_interval_sec = 3
    fast_enemy_spawn_interval_tmr = 0
    boss_spawn_interval_sec = 3
    boss_spawn_interval_tmr = 0
    suvivetime = 0

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_F1:
                max_fps = 60
                print(f"MAX FPS: {max_fps}")
            if event.type == pg.KEYDOWN and event.key == pg.K_F2:
                max_fps = 30
                print(f"MAX FPS: {max_fps}")
            if event.type == pg.KEYDOWN and event.key == pg.K_F3:
                max_fps = 15
                print(f"MAX FPS: {max_fps}")

        if score.score >= 500 and score.score < 1500:
            player.attack_interval = 0.1

        elif score.score >= 1500:
            player.attack_interval = 0.1
            player.attack_number = 3

        # 数秒おきに敵をスポーンさせる処理
        if enemy_spawn_interval_tmr > enemy_spawn_interval_sec:
            # カメラ中心位置から何pxか離れた位置に敵をスポーン
            enemies.add(Enemy(get_random_spawn_pos(), player, effect_group))
            enemy_spawn_interval_tmr = 0
        enemy_spawn_interval_tmr += dtime

        if fast_enemy_spawn_interval_tmr > fast_enemy_spawn_interval_sec:
            enemies.add(Enemy(get_random_spawn_pos(), player, effect_group, speed=300, score=50, hp=10))
            fast_enemy_spawn_interval_tmr = 0
        fast_enemy_spawn_interval_tmr += dtime

        if boss_spawn_interval_tmr > boss_spawn_interval_sec:
            # カメラ中心位置から何pxか離れた位置に敵をスポーン
            enemies.add(BOSS(get_random_spawn_pos(), player, effect_group, flame))
            boss_spawn_interval_tmr = 0
        boss_spawn_interval_tmr += dtime

        # 銃弾とボスの攻撃の当たり判定処理
        pg.sprite.groupcollide(flame, bullets, True, True)


        # 敵とプレイヤーの当たり判定処理
        for _ in pg.sprite.spritecollide(player, enemies, False):
            player.give_damage(10)

        # 背景の更新＆描画処理
        background.update()
        background.draw(screen)

        # ゲームオーバー処理
        # TODO: この位置にゲームオーバーがあるのは何となく微妙なので書き直す
        if player.hp <= 0:
            font = pg.font.Font(None, 250)
            bullet_img = font.render(f"Game Over", 0, (255,0,0))
            img_rct = bullet_img.get_rect()
            img_rct.center = (WIDTH/2, HEIGHT/2)
            screen.blit(bullet_img, img_rct)

            player.change_img(8, 10, 250)
            player.update(key_lst,dtime)
            player_group.draw(screen)
            pg.display.update()
            time.sleep(2)
            return
        
        if int(suvivetime) >= 60:
            gameFlag = True

        font = pg.font.Font(None, 250)
        bullet_img = font.render(f"{int(60 - suvivetime)}", 0, (0,255,0))
        img_rct = bullet_img.get_rect()
        img_rct.center = (WIDTH/2, 100)
        screen.blit(bullet_img, img_rct)
        
        # ゲームクリアの処理
        if gameFlag == True:
            # game clear
            font = pg.font.Font(None, 250)
            bullet_img = font.render(f"Game Clear", 0, (0,255,0))
            img_rct = bullet_img.get_rect()
            img_rct.center = (WIDTH/2, HEIGHT/2)
            screen.blit(bullet_img, img_rct)

            player.change_img(9, 10, 250)
            player.update(key_lst,dtime)
            player_group.draw(screen)
            pg.display.update()
            time.sleep(2)
            return
        
        # プレイヤー更新処理
        player.update(key_lst,dtime)
        camera.update(dtime)

        # 数秒おきにマウス方向に銃弾を飛ばす
        if clk > player.attack_interval:
            clk = 0
            mouse_pos = list(pg.mouse.get_pos())
            mouse_pos[0] -= screen.get_width() / 2
            mouse_pos[1] -= screen.get_height() / 2
            direction =  calc_orientation(player.rect.center, (mouse_pos[0] + camera.center_pos[0], mouse_pos[1] + camera.center_pos[1]))
            angle = math.degrees(math.atan2(direction[1], direction[0]))

            bullet_img = pg.Surface((20, 10))
            pg.draw.rect(bullet_img, (255, 0, 0), bullet_img.get_rect())
            bs = gen_beams(bullet_img, player, angle, enemies, bullet_count=player.attack_number, speed=1000)
            for b in bs:
                bullets.add(b)
            pg.mixer.Sound("ex05/fig/se_bullet.mp3").play()

        # 敵の更新処理
        enemies.update(dtime)
        # 銃弾の更新処理
        bullets.update(dtime, score)
        # ボスの攻撃の更新処理
        flame.update(dtime, score)
        # エフェクトの更新処理
        effect_group.update(dtime)

        # 描画周りの処理
        player_group.draw(screen)
        bullets.draw(screen)
        enemies.draw(screen)
        flame.draw(screen)
        score.update(screen)
        effect_group.draw(screen)
        pg.display.update()

        suvivetime += dtime
        clk += dtime
        dtime = clock.tick(max_fps) / 1000


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
