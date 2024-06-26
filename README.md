# Repository Scripts Documentation

This repository contains two Python helper scripts for VE report generation and to enable DRR in the Algolia dashboard in case the "simulate DRR" button is not active. Below you will find descriptions, usage instructions, and configurations for each script.

## 1. create_report.py

This script aggregates multiple CSV or text files generated by the Algolia VE radar tool into a single Excel file. It also enhances the data with additional columns, calculations, and formatting suitable for uploading to Google Sheets.

### Features

- **Aggregation**: Combines multiple data files into one Excel file.
- **Enhancements**: Adds extra columns, performs calculations, and applies formatting.
- **Google Sheets Ready**: Generates a file ready to be uploaded to Google Sheets.


### Prerequisites

Before running the script, ensure you have:
- Python 3.x
- `pandas` and `xlsxwriter` packages installed.

### Installation

Run the following command to install the necessary packages:

```
pip install pandas xlsxwriter
```


### Usage

To use `create_report.py`, navigate to the directory containing the script and run the following command:

```
python create_report.py <path_to_directory>
```

`<path_to_directory>` should be the path to the directory containing a subdirectory with the radar CSV or text files. The script outputs an Excel file in the same directory.

## 2. Algolia Insights Script to send events and enable DRR

Sometimes you can't enable DRR right from the dashboard, even though there are enough events sent by the Radar tool. You might need to send a few events manually to the index containing your prospects data so that the button becomes active. Be aware that this can take up to a few hours until the dashboard picks it up, therefore there is the option to send events continuously every X seconds. 

### Features

- **Search Functionality**: Performs a search to get a QueryID and displays top 20 results the first time to make sure results are returned.
- **Event Tracking**: Sends `clicked_object_ids_after_search` and `converted_object_ids_after_search` events to the selected Algolia index.

### Prerequisites

Before running the script, ensure you have:
- Python 3.x
- `algoliasearch` packages installed.

### Installation

Run the following command to install the necessary packages:

```
pip install algoliasearch
```


### Usage

Execute the script with:

```
python send_event.py
```

Follow the prompts to enter your Algolia App ID, Admin API Key, and other required information. The script will guide you through performing a search, selecting a result, and sending event data to Algolia.

## Support

For more information or assistance, refer to the [Algolia documentation](https://www.algolia.com/doc/) or contact Andreas De Stefani.


