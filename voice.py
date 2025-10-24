import requests
import json
import os

# --- 定数定義 ---
JSON_DIR = "json"
DEFINE_FILE = os.path.join(JSON_DIR, "define.json")  # APIキーと話者IDが書かれた設定ファイル
VOICE_FILE = os.path.join(JSON_DIR, "voice.json")    # 生成したい音声のリストが書かれたファイル
EXPORT_DIR = "exports"       # .wav ファイルの出力先フォルダ

def main():
    print("--- 音声生成スクリプト開始 ---")

    # --- 1. 出力先フォルダの確認・作成 ---
    try:
        # exist_ok=True にすると、フォルダが既に存在してもエラーにならない
        os.makedirs(EXPORT_DIR, exist_ok=True)
    except OSError as e:
        print(f"エラー: 出力先フォルダ '{EXPORT_DIR}' の作成に失敗しました。")
        print(f"詳細: {e}")
        return  # 処理終了

    # --- 2. define.json からAPIキーと話者IDを読み込む ---
    try:
        with open(DEFINE_FILE, 'r', encoding='utf-8') as f:
            define_data = json.load(f)

        API_KEY = define_data["femalevoice"]["apikey"]
        # speakeridが数値でも文字列でも対応できるように、str()で文字列に変換
        SPEAKER_ID = str(define_data["femalevoice"]["speakerid"])

        if not API_KEY:
            print(f"エラー: '{DEFINE_FILE}' 内の 'apikey' が空です。処理を中断します。")
            return

    except FileNotFoundError:
        print(f"エラー: 設定ファイル '{DEFINE_FILE}' が見つかりません。")
        print(f"（スクリプトと同じ階層の '{JSON_DIR}' フォルダ内にありますか？）")
        return
    except json.JSONDecodeError:
        print(f"エラー: '{DEFINE_FILE}' のJSON形式が正しくありません。")
        return
    except KeyError as e:
        print(f"エラー: '{DEFINE_FILE}' に必要なキー {e} が見つかりません。")
        print("（ 'femalevoice' -> 'apikey' / 'speakerid' の構造か確認してください）")
        return

    print("設定ファイル (define.json) を読み込みました。")

    # --- 3. 残りAPIポイントを確認して表示 ---
    points_check_url = "https://deprecatedapis.tts.quest/v2/api/"
    points_params = {"key": API_KEY}

    print("現在のAPIポイントを確認しています...")
    try:
        points_response = requests.get(points_check_url, params=points_params)

        if points_response.status_code == 200:
            remaining_points = points_response.text
            print(f"✅ 現在の残りAPIポイント: {remaining_points}")
        else:
            # ポイント確認に失敗しても、エラー内容だけ表示して処理は続行
            print(
                f"エラー: APIポイントの確認に失敗しました (ステータスコード: {points_response.status_code})")
            print(f"   エラー内容: {points_response.text}")

    except requests.exceptions.RequestException as e:
        print(f"エラー: APIポイント確認中に通信エラーが発生しました: {e}")

    print("-" * 40)

    # --- 4. voice.json から生成リストを読み込む ---
    try:
        with open(VOICE_FILE, 'r', encoding='utf-8') as f:
            voice_data = json.load(f)

        if not isinstance(voice_data, dict) or not voice_data:
            print(f"エラー: '{VOICE_FILE}' が空か、期待する形式 (辞書) ではありません。")
            return

    except FileNotFoundError:
        print(f"エラー: 音声リストファイル '{VOICE_FILE}' が見つかりません。")
        print(f"（スクリプトと同じ階層の '{JSON_DIR}' フォルダ内にありますか？）")
        return
    except json.JSONDecodeError:
        print(f"エラー: '{VOICE_FILE}' のJSON形式が正しくありません。")
        return

    print(f"'{VOICE_FILE}' を読み込みました。{len(voice_data)} 件の音声を処理します。")

    # --- 5. メインループ: 音声合成処理 ---
    base_url = "https://deprecatedapis.tts.quest/v2/voicevox/audio/"
    success_count = 0
    skip_count = 0
    fail_count = 0

    # voice_data (辞書) のキーと値のペア (例: 'v1-01', {'id': ..., 'context': ...}) を順に処理
    for voice_key, voice_info in voice_data.items():

        # 必要なキー (context, wavName) が存在するかチェック
        try:
            text_to_speak = voice_info["context"]
            wav_name = voice_info["wavName"]
        except TypeError:
            print(f"スキップ: '{voice_key}' のデータ形式が不正です (辞書ではありません)。")
            fail_count += 1
            continue  # 次のループへ
        except KeyError as e:
            print(f"スキップ: '{voice_key}' に必要なキー {e} がありません。")
            fail_count += 1
            continue  # 次のループへ

        # 出力先のフルパスを生成 (例: "exports/voice1-01.wav")
        output_path = os.path.join(EXPORT_DIR, wav_name)

        print(f"\n--- 処理中: {voice_key} (ファイル名: {wav_name}) ---")

        # --- 重複チェック ---
        if os.path.exists(output_path):
            # ターミナルでユーザーに入力を求める
            user_input = input(
                f"ファイル '{output_path}' は既に存在します。再生成しますか？ (y/N): ")

            # 'y' または 'Y' 以外 (無入力, 'n', 'no' など) はスキップ
            if user_input.lower() != 'y':
                print("   スキップしました。")
                skip_count += 1
                continue  # 次のループへ

            print("   上書き再生成します...")

        # --- APIリクエストの実行 ---
        params = {
            "key": API_KEY,
            "speaker": SPEAKER_ID,
            "text": text_to_speak
        }

        try:
            print(f"   APIにリクエストを送信中... (text: {text_to_speak[:30]}...)")
            response = requests.get(base_url, params=params)

            # 4. サーバーからの応答を処理
            if response.status_code == 200:
                # 成功した場合、音声データをファイルに書き込む (バイナリモード 'wb')
                with open(output_path, "wb") as f:
                    f.write(response.content)

                print(f"成功: '{output_path}' を生成しました。")
                success_count += 1

            else:
                # APIがエラーを返した場合
                print(
                    f"失敗: {voice_key} の生成に失敗しました。 (ステータスコード: {response.status_code})")
                print(f"   エラーメッセージ: {response.text}")
                fail_count += 1

        except requests.exceptions.RequestException as e:
            # 通信自体に失敗した場合
            print(f"失敗: {voice_key} のリクエスト中に通信エラーが発生しました: {e}")
            fail_count += 1

    # --- 6. 最終結果の表示 ---
    print("-" * 40)
    print("すべての処理が完了しました。")
    print(f"結果: 成功 {success_count}件, スキップ {skip_count}件, 失敗 {fail_count}件")

# このスクリプトが直接実行された場合にのみ main() 関数を呼び出す
if __name__ == "__main__":
    main()
