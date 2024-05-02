
## This script is used to create an excel report from exported CSV files from VE admin panel.
## Usage: python create_report.py <relative_path>
##
## The script will ask for the sub directory containing the exported CSV files and parameters to use.
##
## Author: Andreas De Stefani, Algolia Solutions Engineering
## Date: 2024-05
## 


import os, sys
import pandas as pd
import xlsxwriter

# ANSI escape codes
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'  # Resets the color to default.

def rename_txt_to_csv(directory):
    """Renames all .txt files in the specified directory to .csv."""
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, filename[:-4] + '.csv')
            os.rename(old_path, new_path)
            print(f"Renamed {filename} to {filename[:-4] + '.csv'}")


def get_subdirectories(directory):
    """
    Returns a list of subdirectories in the given directory.
    """
    return [name for name in os.listdir(directory) 
            if os.path.isdir(os.path.join(directory, name))]




def process_group(group, lcb_treshold=0.35):
    max_h_idx = group['lcb'].idxmax()  # Get the index of the max 'H' value
    max_h_row = group.loc[[max_h_idx]].copy()  # Use loc to get the row and ensure it's a copy
    count_h_above_03 = (group['lcb'] > lcb_treshold).sum()
    max_h_row['no_above_threshold'] = count_h_above_03  # Safely add count to the row
    return max_h_row


def csv_to_xlsx_with_chart(csv_files, output_filename, days=14, lcb_treshold=0.35, min_dollar_amount=5000):
    """
    Combine multiple CSV files into a single XLSX file and add a chart for data in the 'position_bias' sheet.
    
    Args:
    csv_files (list of str): List of paths to CSV files.
    output_filename (str): Path to output XLSX file.
    """
    writer = pd.ExcelWriter(output_filename, engine='xlsxwriter')
    workbook = writer.book
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
    format_light_red = workbook.add_format({'bg_color': '#FFC7CE'})  # Format for conditional formatting
    format_light_green = workbook.add_format({'bg_color': '#a4cc9f'})

    rerank_candidates_list = []
    rerank_candidates_df = None

    total_rev_uplift = 0
    total_search_uplift = 0
    total_candidate_uplift = 0

    #make sure insights are loaded first
    csv_files.sort(key=lambda x: 'insights' not in x)
    
    for csv_file in csv_files:
        sheet_name = os.path.splitext(os.path.basename(csv_file))[0]
        print(f"reading sheet {Colors.GREEN}{sheet_name}{Colors.RESET}")
        if '_' in sheet_name:
            sheet_name = '_'.join(sheet_name.split('_')[1:])
        df = pd.read_csv(csv_file)
        if sheet_name == 'position_bias':
            df = df.sort_values(by=df.columns[0])

        if sheet_name == 'query_insights':
            if 'revenue_after_multiplier' in df.columns:
                col_name = 'annualized uplift after multiplier'
                df[col_name] = ((df['revenue_after_multiplier'] / days) * 365).astype(int)
            # Get values from column 'C' where 'Q' < 'P' and 'AG' >= 10000
            
            rerank_candidates_list = df.loc[(df['conversion_rate'] < df['ctr']) & (df[col_name] > min_dollar_amount), 'query_fingerprint'].tolist()
            query_uplift = df.set_index('query_fingerprint')[col_name].to_dict()
            total_rev_uplift = df[col_name].sum()

            search_df = df[df['is_category_page'] == False]
            total_search_uplift = search_df[col_name].sum()

        if sheet_name == 'query_reranking':
            rerank_candidates_df = df[df['query_fingerprint'].isin(rerank_candidates_list)].copy()
            rerank_candidates_df['annualized_uplift'] = rerank_candidates_df['query_fingerprint'].map(query_uplift)
            
        
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    print('')
    print(f"{Colors.RED}looking for value ... {Colors.RESET}", end='')
    # Further filter to find groups with at least 3 entries where 'H' > 0.3
    # Group by 'A' and filter groups
    
    result_groups = rerank_candidates_df.groupby('query_fingerprint').filter(lambda x: (x['lcb'] > lcb_treshold).sum() >= 3)
    # Apply the function to each group and concatenate the results
    result_df = pd.concat([process_group(group, lcb_treshold) for name, group in result_groups.groupby('query_fingerprint')])
    total_candidate_uplift = result_df['annualized_uplift'].sum()
    result_df.to_excel(writer, sheet_name='rerank_candidates', index=False)

    #add a new sheet for Summary as first sheet
    summary_data = {
        'total_rev_uplift': [total_rev_uplift],
        'total_search_uplift': [total_search_uplift],
        'total_browsed_uplift': [total_rev_uplift - total_search_uplift], 
        'total_candidate_uplift': [total_candidate_uplift]
    }

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    # Add a chart to the position_bias sheet if it exists
    if 'position_bias' in writer.sheets:
        worksheet = writer.sheets['position_bias']
        max_row = len(df) + 1
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Click share',
            'pos': f'=position_bias!$A$2:$A$11',
            'values':     f'=position_bias!$E$2:$E$11',
        })
        chart.add_series({
            'name': 'Conversion share',
            'pos': f'=position_bias!$A$2:$A$11',
            'values': f'=position_bias!$G$2:$G$11',
        })
        chart.set_x_axis({'name': 'Position'})
        chart.set_y_axis({
            'name': 'Value',
            'min': 0,    # Set the minimum value of the y-axis
            'max': 1,  # Set the maximum value of the y-axis
            'major_unit': 0.1,  # Set the interval between major ticks on the y-axis
        })
        chart.set_title({'name': 'Position Bias'})
        worksheet.insert_chart('I2', chart)

    if 'query_insights' in writer.sheets:
                # Add conditional formatting to "query_insights" sheet specifically
        qis = writer.sheets['query_insights']
        # Apply conditional formatting based on values in column P and O
        qis.conditional_format(1, 16, len(df), 16, {
            'type': 'formula',
            'criteria': '=Q2<O2',
            'format': format_light_red
        })

        qis.conditional_format(1, 32, len(df), 32, {
            'type': 'cell',
            'criteria': '>',
            'value': min_dollar_amount,
            'format': format_light_green
        })

        
    writer.close()
    print(f"{Colors.BLUE}f{Colors.GREEN}o{Colors.RED}u{Colors.YELLOW}n{Colors.BLUE}d{Colors.GREEN} i{Colors.RED}t!{Colors.RESET}")


def get_working_directory():
    # Check if a command-line argument is provided and change current working directory if so.
    if len(sys.argv) < 2:
        print('')
        print("No relative path provided. Using current working directory.")
        print("You can provide a relative path as an argument, containing a subdirectory containing exported report files.")
        print("Usage: python create_report.py <relative_path>")
        print('')
    else:
        relative_path = sys.argv[1]
        new_working_directory = os.path.abspath(relative_path)
        os.chdir(new_working_directory)
        print("Changed working directory to:", os.getcwd())


    current_directory = os.getcwd()
    subdirectories = list(reversed(get_subdirectories(current_directory)))
    default_subdirectory = "."
    if subdirectories:
        default_subdirectory = subdirectories[0]
    #display the subdirectories
    print('')
    print("Subdirectories in the current directory:")
    for i, subdirectory in enumerate(subdirectories, 1):
        print(f">> {subdirectory}")

    input_directory = input(f"Enter the sub-directory containing your report files: [{default_subdirectory}] ").strip()
    print('')
    if not input_directory:
        input_directory = default_subdirectory
    return input_directory



if __name__ == "__main__":

    days = 14
    lcb_treshold = 0.3
    min_dollar_amount = 5000

    print("Welcome to the VE report creator!")
    print('---------------------------------')

    input_directory = get_working_directory()
    
    file_format = input("What format are the files in? Enter 'csv' or 'txt': ").strip().lower()
    if file_format not in ['csv', 'txt']:
        file_format = 'txt'
    if file_format == 'txt':
        rename_txt_to_csv(input_directory)
        print("Renamed all .txt files to .csv.")
    csv_files = [os.path.join(input_directory, f) for f in os.listdir(input_directory) if f.endswith('.csv')]
    if len(csv_files) < 5:
        #ask if there are files missing and if they want to abort
        print("There are less than 5 CSV files in the specified directory.")
        print("Please make sure you have all the necessary files.")
        print("If you are missing files, please add them to the directory and run the script again.")
        print("")
    
    print('')
    input_days = input("How many days of data are you looking at? [14] ")
    print('')
    if input_days:
        try:
            days = int(input_days)
        except ValueError:
            print("Invalid input. Using default value of 14.")
            days = 14
    else:
        days = 14

    input_lcb_treshold = input(f"Enter the LCB threshold for rerank candidates [{lcb_treshold}]: ")    
    
    if input_lcb_treshold:
        try:
            lcb_treshold = float(input_lcb_treshold)
        except ValueError:
            print("Invalid input. Using default value of ", lcb_treshold)

    input_min_dollar_amount = input("Enter the minimum dollar amount for rerank candidates [5000]: ")
    if input_min_dollar_amount:
        try:
            min_dollar_amount = int(input_min_dollar_amount)
        except ValueError:
            print("Invalid input. Using default value of ", min_dollar_amount)


    cwd = os.getcwd()
    directory_name = os.path.basename(cwd)
    default_filename = f"{directory_name}.xlsx"
    print('')
    print('')
    output_filename = input(f"Enter output filename or press enter to use '{default_filename}': ").strip() or default_filename
    print('')
    print("starting...")
    print('')

    if not csv_files:
        print("No CSV files found in the specified directory.")
    else:
        csv_to_xlsx_with_chart(csv_files, output_filename, days, lcb_treshold, min_dollar_amount)
        print(f"Created {Colors.GREEN}{output_filename}{Colors.RESET} with sheets and charts where applicable.")
    print('')
    print('')


    