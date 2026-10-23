import asyncio
import csv
import json
import os

from playwright.async_api import async_playwright

class DMMPurchaseHistory:
    def __init__(self, page):
        self.page = page

    async def navigate_to_history(self):
        await self.page.goto("https://payment.dmm.com/history/")
        try:
            await asyncio.sleep(4)
            print("購入履歴ページに移動しました")
        except Exception as e:
            print(f"ページ移動中にエラーが発生しました: {e}")

    async def collect_data(self):
        all_data = []

        selects = await self.page.locator("select").all()
        target_select = None
        
        for sel in selects:
            text = await sel.inner_text()
            if "年" in text or "月" in text or "すべて" in text:
                target_select = sel
                break
        
        if not target_select and selects:
            target_select = selects[0]

        if target_select:
            options = await target_select.locator("option").all()
            values_texts = []
            for opt in options:
                val = await opt.get_attribute("value")
                text = await opt.inner_text()
                if val: 
                    values_texts.append((val, text.strip()))
            
            print(f"取得対象の期間が {len(values_texts)} 件見つかりました。順次取得を開始します...")

            for val, text in values_texts:
                print(f"--- 【{text}】 のデータを取得中 ---")
                try:
                    await target_select.select_option(val)
                    await self.page.wait_for_load_state("networkidle")
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"プルダウンの変更に失敗しました: {e}")
                    continue
                
                month_data = await self._load_all_and_collect_current_view()
                all_data.extend(month_data)
        else:
            print("期間選択のプルダウンが見つかりませんでした。現在表示されている期間のみ取得します。")
            month_data = await self._load_all_and_collect_current_view()
            all_data.extend(month_data)

        return all_data

    async def _load_all_and_collect_current_view(self):
        # 履歴の要素を特定するセレクタ
        row_selector = "table tr, .list-box, .purchase-list-item"
        
        while True:
            await asyncio.sleep(2)
            
            # 【追加】クリック前の履歴件数を取得
            current_items_count = await self.page.locator(row_selector).count()
            
            # 汎用的なテキスト検索ではなく、表示されている最初の「もっと見る」を厳密に狙う
            more_button = self.page.locator("text='もっと見る'").first
            
            is_visible = await more_button.is_visible()
            if is_visible:
                print("  -> 「もっと見る」をクリックして追加読み込みします...")
                try:
                    # 強制的にクリックイベントを発火させる (force=True)
                    await more_button.scroll_into_view_if_needed()
                    await more_button.click(force=True, timeout=5000)
                    
                    # 読み込みを待つ
                    await asyncio.sleep(3)
                    
                    # 【追加】クリック後の履歴件数を取得して比較
                    new_items_count = await self.page.locator(row_selector).count()
                    if new_items_count <= current_items_count:
                        print("  -> これ以上データが増えないため、読み込みを終了します。")
                        break
                        
                except Exception as e:
                    print(f"  -> ボタンのクリック処理を終了します: {e}")
                    break
            else:
                break
                
        # 展開しきった後に画面内のデータを一括取得
        view_data = []
        rows = await self.page.query_selector_all(row_selector)
        
        for row in rows:
            text_content = await row.inner_text()
            cleaned_row = [t.strip() for t in text_content.split('\n') if t.strip()]
            
            if cleaned_row and len(cleaned_row) > 1:
                view_data.append(cleaned_row)
                
        return view_data

async def main():
    email = input("DMMのメールアドレスを入力してください: ")
    password = input("DMMのパスワードを入力してください: ")

    login_url = "https://payment.dmm.com/history/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        if os.path.exists("dmm_cookies.json"):
            with open("dmm_cookies.json", "r") as f:
                cookies = json.load(f)
            await page.context.add_cookies(cookies)
            print("クッキーを読み込みました")
        else:
            await page.goto(login_url)
            await page.fill('input[name="login_id"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button:text("ログイン")')
            print("ログイン完了")
            
            await asyncio.sleep(15)
            
            cookies = await page.context.cookies()
            with open("dmm_cookies.json", "w") as f:
                json.dump(cookies, f)
                print("クッキーを保存しました")

        dmm_history = DMMPurchaseHistory(page)
        await dmm_history.navigate_to_history()
        data = await dmm_history.collect_data()
        await browser.close()

        if data:
            max_cols = max(len(row) for row in data)
            header = [f"データ{i+1}" for i in range(max_cols)]

            with open("output.csv", "w", newline="", encoding="utf-8-sig") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)
                for row in data:
                    padded_row = row + [""] * (max_cols - len(row))
                    writer.writerow(padded_row)
            print("全ての購入履歴を output.csv に出力しました。")
        else:
            print("データが取得できませんでした。")

if __name__ == "__main__":
    asyncio.run(main())