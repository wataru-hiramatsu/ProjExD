# こうかとんサバイバー
## 実行環境の必要条件
* python >= 3.10
* pygame >= 2.1

## ゲームの概要
プレイヤーをWASDキーで操作して迫りくる敵を銃弾で倒し、1分間生き残るゲームです。

ステージは見下ろし型で、常にプレイヤーを中心として表示されます。

マウスを使い、銃弾を放つ方向を決めることができます。

敵を倒していくと、上部にあるゲージがたまっていきます。

倒した敵の数に応じてゲージがたまり、弾数が増えていきます。


## ゲームの実装

### 共通基本機能
* Characterクラス（PlayerとEnemyの基底クラス）
* Playerクラス
* Enemyクラス
* Bulletクラス
* ゲームオーバー機能

### 追加機能
* HPバー(平松 C0B22124)
* カメラスクロール機能(平松 C0B22124)
* プレイヤーのマウス方向への攻撃(平松 C0B22124)
* プレイヤーの攻撃がscoreに応じで変化する(後藤 C0B22064)
* 各種サウンド(アハメド c0b21010)
* ボス(三樹 C0B21147)
* ボスの攻撃(三樹 C0B21147)
* スコア機能(後藤 C0B22064)
* 可変フレームレート(茅野 C0B22100)
* クリア演出(茅野 C0B22100)
### ToDo

### メモ
