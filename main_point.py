import asyncio
import csv
import json
import os

from playwright.async_api import async_playwright

class DMMPurchaseHistory:
    def __init__(self, page):
        self.page = page

    async def navigate_to_history(self):
        await self.page.goto("https://www.pointclub.dmm.com/management/history#use-info")
        try:
            await self.page.wait_for_selector(".HistoryPointList_form__24Kzv", timeout=15000)
            print("購入履歴ページに移動しました")
        except Exception as e:
            print(f"ページ移動中にタイムアウトまたはエラーが発生しました: {e}")

    async def collect_data(self):
        all_data = []

        # 1. 「購入したポイント」フィルタの選択
        try:
            filter_btn = self.page.locator("button.HistoryPointList_filter_button__H_ooI", has_text="購入したポイント")
            if await filter_btn.is_visible():
                await filter_btn.click(force=True)
                await self.page.wait_for_timeout(2000)
                print("「購入したポイント」でフィルタリングしました")
        except Exception as e:
            print(f"フィルタリング選択に失敗しました: {e}")

        # 2. 年プルダウンから選択肢を取得 (v3の成功ロジックを復元)
        years = []
        try:
            select_boxes = self.page.locator(".SelectBox_wrapper__qJJsS")
            year_select_box = None
            
            count = await select_boxes.count()
            for i in range(count):
                sb = select_boxes.nth(i)
                txt = await sb.inner_text()
                if "年" in txt:
                    year_select_box = sb
                    break
            
            if not year_select_box and count > 0:
                year_select_box = select_boxes.nth(0)

            if year_select_box:
                # ドロップダウンを開く
                await year_select_box.click(force=True)
                await self.page.wait_for_timeout(1000)

                # v3で成功していた柔軟なセレクタ
                options = year_select_box.locator("div[role='option'], .SelectBox_value_text__B1Ol3")
                opt_count = await options.count()

                for i in range(opt_count):
                    opt_text = await options.nth(i).inner_text()
                    opt_text_clean = opt_text.strip()
                    if opt_text_clean and "年" in opt_text_clean and opt_text_clean not in years:
                        years.append(opt_text_clean)

                # v5のクラッシュ対策：Escapeキーで安全にドロップダウンを閉じる
                await self.page.keyboard.press("Escape")
                await self.page.wait_for_timeout(500)
        except Exception as e:
            print(f"年の取得中にエラーが発生しました: {e}")

        # 3. 年ごとにデータを取得
        if years:
            print(f"取得対象の年が {len(years)} 件見つかりました ({', '.join(years)})。順次取得を開始します...")
            
            for year in years:
                print(f"\n--- 【{year}】 のデータを取得中 ---")
                try:
                    # 対象の年を選択
                    await year_select_box.click(force=True)
                    await self.page.wait_for_timeout(1000)
                    
                    # v3で成功していたセレクタを使用
                    target_opt = year_select_box.locator(f"div[role='option']:has-text('{year}'), .SelectBox_value_text__B1Ol3:has-text('{year}')").first
                    await target_opt.click(force=True)
                    # 切り替え後の読み込みを待機
                    await self.page.wait_for_timeout(2500)
                except Exception as e:
                    print(f"年 {year} の選択に失敗しました: {e}")
                    continue

                # ページネーションを辿って取得 (v5の成功ロジック)
                year_data = await self._collect_pages()
                all_data.extend(year_data)
        else:
            print("年の選択肢が検出できなかったため、現在表示中の画面から取得を実行します...")
            current_data = await self._collect_pages()
            all_data.extend(current_data)

        return all_data

    async def _collect_pages(self):
        page_data = []
        row_selector = ".HistoryPointList_box_list__EhNjO tbody tr"

        page_num = 1
        while True:
            await self.page.wait_for_timeout(1500)

            # 現在ページの行を取得
            rows = await self.page.query_selector_all(row_selector)
            added_in_this_page = 0
            for row in rows:
                text_content = await row.inner_text()
                cleaned_row = [t.strip() for t in text_content.split('\n') if t.strip()]
                if cleaned_row:
                    page_data.append(cleaned_row)
                    added_in_this_page += 1

            print(f"  -> ページ {page_num}: {added_in_this_page} 件取得")

            # ページネーション処理（「>」ボタン）
            next_li = self.page.locator("li.paginate_next_list")
            
            if await next_li.count() > 0:
                class_attr = await next_li.get_attribute("class") or ""
                # disabledクラスが付与されている場合は最終ページ
                if "disabled" in class_attr:
                    print(f"  -> 【完了】これ以上進むページがありません。")
                    break
                else:
                    # 次のページへ進む
                    next_link = next_li.locator("a")
                    if await next_link.count() > 0 and await next_link.is_visible():
                        print(f"  -> {page_num + 1}ページ目へ遷移します...")
                        await next_link.click(force=True)
                        page_num += 1
                        await self.page.wait_for_timeout(2500)
                    else:
                        break
            else:
                # ページネーション自体が存在しない場合
                break

        return page_data


async def main():
    email = input("DMMのメールアドレスを入力してください: ")
    password = input("DMMのパスワードを入力してください: ")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        if os.path.exists("dmm_cookies.json"):
            with open("dmm_cookies.json", "r") as f:
                cookies = json.load(f)
            await page.context.add_cookies(cookies)
            print("クッキーを読み込みました")
        else:
            await page.goto("https://accounts.dmm.com/service/login/password")
            await page.fill('input[name="login_id"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"], input[type="submit"]')

            print("ログイン処理を実行しました。2段階認証などが求められた場合は15秒以内に手動で完了させてください。")
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
            print(f"\n合計 {len(data)} 件の購入履歴を output.csv に出力しました。")
        else:
            print("データが取得できませんでした。")

if __name__ == "__main__":
    asyncio.run(main())
