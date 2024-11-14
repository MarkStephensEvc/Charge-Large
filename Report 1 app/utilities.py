#utilities.py
#import module
import pandas as pd
import geopandas as gpd
import numpy as np
import plotly.express as px
import re
import os
import base64
#import functions
from plotly import graph_objects as go
from config import * 
from pathlib import Path
from io import BytesIO
from azure.storage.blob import BlobServiceClient

# Function to convert PNG image to base64
def convert_image_to_base64(image_file, container_name="your-container-name", local_env = True):
    #local environment 
    if local_env:
        app_dir = Path(__file__).parent
        # Path to the image in the 'img' directory
        icon_path = app_dir / "img" / image_file
        with open(icon_path, "rb") as image:
            return base64.b64encode(image.read()).decode("utf-8")
    else:
        blob_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=f"img/{image_file}")
        blob_data = blob_client.download_blob().readall()
        return base64.b64encode(blob_data).decode("utf-8")

# list of months for ui input values    
def generate_month_dates(df, datetime_col):
    """
    Generates a list of datetime objects for the start of each month within the range
    of years found in the specified datetime column.

    Args:
        df (pd.DataFrame): The DataFrame containing the datetime column.
        datetime_col (str): The name of the column with datetime information.

    Returns:
        list: List of datetime objects for the start of each month within the date range.
    """
    # Ensure the datetime column is in datetime format
    df[datetime_col] = pd.to_datetime(df[datetime_col])

    # Extract the minimum and maximum month and year
    start_year = df[datetime_col].dt.year.min()
    end_year = df[datetime_col].dt.year.max()
    
    # Define the start and end of the range
    start_date = pd.Timestamp(year=start_year, month=1, day=1, tz='UTC')
    end_date = pd.Timestamp(year=end_year, month=12, day=31, tz='UTC')

    # Generate a range of dates for the start of each month
    month_dates = pd.date_range(start=start_date, end=end_date, freq='MS')

    # Convert the result to a list of datetime objects
    return month_dates.tolist()


def convert_dataframe_timezone(df, datetime_col, state_col):
    """
    Converts a DataFrame datetime column from UTC to a target timezone based on the provided state.
    
    Args:
        df (pd.DataFrame): The input DataFrame.
        datetime_col (str): The name of the datetime column in the DataFrame.
        state_col (str): The name of the state column in the DataFrame.

    Returns:
        pd.DataFrame: DataFrame with the datetime column converted to the target timezone.
    """
    # Ensure datetime_column is in datetime format with UTC timezone
    df[datetime_col] = pd.to_datetime(df[datetime_col], utc=True)
   
    # Apply timezone conversion based on state
    df[datetime_col] = df.apply(
        lambda row: row[datetime_col].astimezone(timezone_mappings.get(row[state_col], pytz.UTC)),
        axis=1
    )
    return df

def clean_string(value):
    """
    Removes non-permitted characters from a string.
    Only allows letters, numbers, and underscores in the value.
    
    Parameters:
    value (str): The string to clean.
    
    Returns:
    str: The cleaned string.
    """
    # Define regex pattern to keep only letters, numbers, and underscores
    permitted_pattern = re.compile(r'[^a-zA-Z0-9_]')
    # Apply the regex to remove non-permitted characters
    cleaned_value = re.sub(permitted_pattern, '', value)
    return cleaned_value

def load_and_prepare_data(local_env = True,container_name="your-container-name"):
    """
    Loads and prepares data files stored in Azure Blob Storage.
    Parameters:
    local_env (bool): A flag to determine the programming environment 
    Returns:
        Tuple containing DataFrames and dictionaries used in the app.
    """
    ##### Local Environment
    if local_env:
        # Load data and compute static values
        app_dir = Path(__file__).parent
        months_data = pd.read_csv(app_dir / "final_processed_data.csv")
        #load geojson - lga
        geodf_filter_lga = gpd.read_file(app_dir / 'geodf_lga_filter.json')
        geodf_filter_lga.set_index('LGA_name',inplace = True)
        #load geojson - poa
        geodf_filter_poa = gpd.read_file(app_dir / 'geodf_poa_filter.json')
        geodf_filter_poa.set_index('postcode',inplace = True)
        #load lga geocoords
        lga_geogcoord_df = pd.read_csv(app_dir / "lga_geogcoord_df.csv")
        
    ##### Cloud Environment
    else:
    # Retrieve Azure Blob Storage connection details
        blob_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_CONTAINER_NAME", container_name)
        
        # Initialize Blob Service Client
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        
        # Function to download and read a blob file as a DataFrame
        def download_blob_to_dataframe(blob_name, is_geojson=False):
            try:
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
                blob_data = blob_client.download_blob().readall()
                if is_geojson:
                    return gpd.read_file(BytesIO(blob_data))
                return pd.read_csv(BytesIO(blob_data))
            except Exception as e:
                print(f"Error downloading blob {blob_name}: {e}")
                return pd.DataFrame()  # Return an empty DataFrame or handle as needed
        
        # Download CSV and GeoJSON files
        months_data = download_blob_to_dataframe("final_processed_data.csv")
        geodf_filter_lga = download_blob_to_dataframe("geodf_lga_filter.json", is_geojson=True).set_index('LGA_name')
        geodf_filter_poa = download_blob_to_dataframe("geodf_poa_filter.json", is_geojson=True).set_index('postcode')
        lga_geogcoord_df = download_blob_to_dataframe("lga_geogcoord_df.csv")
    
    # Apply timezone conversion
    months_data = convert_dataframe_timezone(months_data, 'interval', 'state')
    
    # LGA and lon lat coords
    lga_geogcoord_dict = {
    row['lga_name']: {  # Outer dictionary key from col1
        'lat': row['lat'],  # Inner dictionary key from col2
        'lon': row['lon']   # Inner dictionary key from col3
    }
    for _, row in lga_geogcoord_df.iterrows()
    }
    # postcode and suburb dictionary
    poa_suburb = { row['postcode']:row['address2'] for _,row in months_data[['postcode','address2']].drop_duplicates().iterrows() }
    
    return months_data, lga_geogcoord_dict, poa_suburb, geodf_filter_lga, geodf_filter_poa


# Process Dataframe based on filters
def process_data(df: pd.DataFrame,
                 agg_cols: list,
                 interval_option: object,
                 combine_cols: bool,
                 time_col = 'interval',
                 var_col = 'variable') -> pd.DataFrame:
    """_summary_

    Args:
        df (pd.DataFrame): _description_
        agg_cols (list): _description_
        interval_option (object): _description_
        combine_cols (bool): _description_
        time_col (str, optional): _description_. Defaults to 'interval'.
        status_col (str, optional): _description_. Defaults to 'variable'.

    Returns:
        pd.DataFrame: _description_
    """
    status_cols = [col for col in df.variable.unique() if col != 'evse_port_site_count']    
    # aggregate data on agg list cols
    df_edit = (df.groupby(agg_cols+[time_col,var_col])['value'].sum().reset_index())
    # list indexing cols
    index_cols = [col for col in df_edit.columns if col not in ['value','variable']]
    # Convert summary data to wide form
    df_edit = df_edit.pivot(index = index_cols, columns = var_col, values = 'value')         
    df_edit = df_edit.reset_index() 
    # check to combine status columns
    if combine_cols:
        # Engineer variables - combined columns
        df_edit['in_use'] = (df_edit['Charging'] +
                            df_edit['Finishing'] +
                            df_edit['Reserved'])
        
        df_edit['unavailable_out_of_order'] = (df_edit['Unavailable'] +
                                            df_edit['Out of order'])
        
        df_edit = df_edit.drop(columns = ['Charging',
                                        'Finishing',
                                        'Reserved',
                                        'Unavailable',
                                        'Out of order'])
        status_cols = ['in_use','unavailable_out_of_order','Available','Unknown','Total']
    #### Aggregate over different intervals
    df_edit_resampled = df_edit.set_index(time_col)
    df_edit_resampled = (
        df_edit_resampled
        .groupby(agg_cols+['evse_port_site_count'])[status_cols]
        .resample(interval_option)
        .sum()
        .reset_index()
    )   
    # Form proportion of Total column
    for col in status_cols:
        df_edit_resampled.loc[:,col] = np.round(df_edit_resampled[col]*100 / df_edit_resampled['Total'],2)
        processed_data = df_edit_resampled.drop(columns=['Total'])
    
    return processed_data  
 
#helper function to plot chloropleth map
def plot_chloropleth_map(df1: pd.DataFrame,
                         df2: pd.DataFrame,
                         geo_df:pd.DataFrame,
                         lga_geogcoord_dict: dict,
                         status_prop: str,
                         lga_name: str,
                         poa_suburb: dict
                         ) -> go.Figure:
    """_summary_
    Args:
        df (pd.DataFrame): _description_
        geo_df (pd.Dataframe): _description_
        lga_geogcoord_dict (dict): _description_
        status_prop (str): _description_
    Returns:
        object: _description_
    """
    
     # Add 'suburb_name' column by mapping 'postcode' to 'poa_suburb'
    df1['suburb_name'] = df1['postcode'].map(poa_suburb)
    
    color_scale = {"in_use": "Greens", "Available": "Blues", "unavailable_out_of_order": "Reds"}.get(status_prop)
    if status_prop == "in_use":
        
        range_color = (0, df1[status_prop].max())
    elif status_prop == "Available":
        range_color = (0, df1[status_prop].max())
    elif status_prop == "unavailable_out_of_order":
        range_color = (0, df1[status_prop].max())
    else:
        range_color = (0, 100)
                       
    map_fig = px.choropleth_mapbox(
            df1,
            geojson = geo_df.geometry,
            locations = 'postcode',
            color = status_prop,
            color_continuous_scale = color_scale,
            range_color = range_color,
            labels = utilisation_status | var_labels,
            hover_name = 'suburb_name',
            hover_data={"evse_port_site_count": True,
                        'postcode': True,
                        'in_use':True,
                        'unavailable_out_of_order': True,
                        'Available': True},
            opacity=0.5,
            center=lga_geogcoord_dict[lga_name], #center of Australia
            #mapbox_style="open-street-map",
            mapbox_style="carto-positron",
            zoom=8,
        )
      # Hide color bar in choropleth
    map_fig.update_layout(coloraxis_showscale=False)
        # Add scatter plot (coordinates) on top of the choropleth map
    scatter_fig = px.scatter_mapbox(df2, 
                            lat="latitude", 
                            lon="longitude", 
                            text="cpo_name",
                            labels = utilisation_status | var_labels,
                            hover_data= {"evse_port_site_count": True,
                                         'postcode': False,
                                         'address1': True,
                                         'address2': True,
                                         'latitude': False, 
                                         'longitude':False,
                                         status_prop:True
                                         }
                            )
    # Set showlegend=False on the scatter plot
    scatter_fig.update_traces(showlegend=False)    
    # Combine the two plots (choropleth and scatter points)
    map_fig.add_trace(scatter_fig.data[0])
    map_fig.update_layout(
        showlegend=False,
        margin={"r": 20, "t": 15, "l": 20, "b": 15})
    
    return map_fig

# Adding a custom function for week of the month calculation
def week_of_month(date):
    first_day = date.replace(day=1)
    return (date.day - 1) // 7 + 1

#helper function to plot chloropleth map
def plot_column_graph(df1: pd.DataFrame,
                      status_prop: str,
                      threshold: int,
                      interval_option: str,
                      selected_period: tuple,
                      ) -> go.Figure:
    """
    Plots a bar graph showing the mean and standard deviation of a specified status property 
    for each period based on the given interval option, with a threshold line.

    Args:
        df1 (pd.DataFrame): Input data containing 'interval' and 'status_prop' columns.
        status_prop (str): Column name for the status property to be plotted.
        threshold (int): Threshold value for the horizontal line.
        interval_option (str): Interval option key for grouping the data.

    Returns:
        go.Figure: A Plotly Figure object with the bar chart and threshold line.
    """
    
    # Ensure your DataFrame is sorted by 'cpo_name' and 'interval' (or any other ordering you prefer)
    df1 = df1.sort_values(by=['cpo_name', 'interval'])
    # Define a mapping for interval options to datetime attributes
    interval_extraction = {
        "60min": df1['interval'].dt.hour + 1,  # Extract hour of day
        "1440min": df1['interval'].dt.dayofweek + 1,  # Extract day of the week
        "10080min": df1['interval'].apply(week_of_month),  # Extract week of the month
        "ME": df1['interval'].dt.month - selected_period[0] + 1,  # Extract month
        "Q": df1['interval'].dt.quarter,  # Extract quarter
        "Y": df1['interval'].dt.year  # Extract year
    }  
    # Use groupby and cumcount to generate a sequential number for each unique 'interval' within each 'cpo_name' group
    df1['period_number'] = interval_extraction.get(interval_option, df1['interval'].dt.hour)
    # plot average across period number
    plot_data = (df1
                 .groupby(['cpo_name','period_number'])[status_prop]
                 .agg(mean_status = 'mean',  std_status = 'std', count_status = 'count')
                 .reset_index()
                 )
    plot_data['std_err'] = plot_data['std_status']/np.sqrt(plot_data['count_status'])
    label = {'period_number':interval_options2[interval_option],status_prop: f'Mean {status_prop}', 'mean_status':'Average value'}    
    
    col_fig = px.bar(
        plot_data,
        x = 'period_number',
        y = 'mean_status',
        labels = utilisation_status | var_labels | label,
        color = 'cpo_name',
        error_y = 'std_err',
        barmode="group",
    title=f"Average {utilisation_status[status_prop]} by {interval_options2[interval_option].capitalize()}"  
        )
    
    # Update layout to position the legend at the top
    col_fig.update_layout(
    title=dict(
        y=1.0,  # Position title higher up
        x=0.5,   # Center the title horizontally
        xanchor="center",
        yanchor="top",
        font=dict(size=16)  # Customize title font size
    ),
    legend=dict(
        title = None,
        orientation="h",    # Horizontal orientation for the legend
        yanchor="top",      # Align the bottom of the legend box
        y=1.05,             # Position the legend below the title
        xanchor="center",   # Center the legend horizontally
        x=0.5               # Center position horizontally
    ),
    margin=dict(t=60, b=40)  # Adjust margins to fit the title and legend
)
    
    # Add a horizontal dashed red line for the threshold
    col_fig.add_shape(
        type="line",
        x0=0, x1=plot_data['period_number'].max()+1,
        y0=threshold, y1=threshold,
        line=dict(color="red", width=2, dash="dash"),
        name="Threshold"
    )
    
    # Add an annotation near the threshold line
    col_fig.add_annotation(
        x=0.99,  # Position in the middle of the x-axis
        y=threshold*0.95,
        xref="paper",  # x is relative to the plot width
        yref="y",  # y is on the y-axis scale
        text=f"Threshold: {threshold: 0.1f}%",
        showarrow=False,
        font=dict(color="red"),
        align="center",
        bgcolor="rgba(255,255,255,0.6)",  # Semi-transparent background
        bordercolor="red",
        borderwidth=1
    )
    # Ensure all x-axis labels are shown
    col_fig.update_xaxes(
        tickmode="linear",
        
    )
    return col_fig