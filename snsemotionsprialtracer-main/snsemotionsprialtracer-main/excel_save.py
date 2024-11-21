import pandas as pd

# 엑셀 파일 경로
excel_file = 'test/generated_images/복사본.xlsx'

# 모든 시트 읽기
dfs = pd.read_excel(excel_file, sheet_name=None)  # sheet_name=None으로 설정하면 모든 시트를 읽음

combined_df = pd.concat(dfs.values(), ignore_index=True)

combined_df.to_csv('current_data.csv', index=False)

    