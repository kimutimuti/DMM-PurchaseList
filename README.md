# DMM_PURCHASELIST

## 注意
このリポジトリは「DMM-PurchaseList」を通常の購入履歴とポイント購入履歴の2つに使えるようにしたフォークです。自分用に作ったものを適当に汎用化しているだけで、安全性については考慮しておりませんので悪しからず。
- また変更にかなりAIを使っているので、ご使用の際はそれを了承してお使いください。
<br>

#### 主な変更点
- 対象を同人購入リストからDMM全体の購入履歴（<https://payment.dmm.com/history/>）とDMMポイントクラブのポイント購入履歴（<https://www.pointclub.dmm.com/management/history#use-info>）へと変化
- 必要なライブラリが`playwright`のみだったので`req.txt`の削除
- 上記に伴う`README.md`の改変


## 概要

DMMの購入履歴（`main.py`）とポイント購入履歴（`main_point.py`）を取得するためのスクリプトです。  
前者だとポイントでの購入も全体の購入履歴に表記されてしまうので後者を用意しました。  
メールアドレス、パスワードを入れて使用します。  
~~おそらく、二段階認証が有効な場合は使えないと思います。~~  
`main_point.py`の方は使えるかも？

## 使い方

1. `cmd`または`PowerShell`を開いてください。
2. 必要なライブラリをインストールします。  
   ```python
   py -m pip install playwright
   ```
3. 次にplaywrightの必要なファイルをダウンロードします。
   ```
   playwright install chromium
   ```
4. ```python
   py main.py
   ```
   または
   ```python
   py main_point.py
   ```
   を実行します。
5. `output.csv` が生成されます。  
   おわり。


## 追記

うまくいかない場合はディレクトリが違う可能性があります。  
`cd <ディレクトリパス>`をしてから実行してください。  
`2025/02/01`:seleniumからplaywrghtでの実装に変更。
