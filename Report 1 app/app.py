#app.py
import faicons as fa
import pandas as pd
from shiny import App, Inputs, Outputs, Session, render, ui, reactive
from shinywidgets import output_widget, render_widget
from config import *
from utilities import *

#local_env = os.getenv("LOCAL_ENV", "True").lower() == "true"
# Load data and compute static values
months_data, lga_geogcoord_dict, poa_suburb, geodf_filter_lga, geodf_filter_poa = load_and_prepare_data(local_env = True) # load_and_prepare_data(local_env=local_env)

# Extract the month numbers for start and end
start_month = months_data['interval'].dt.month.min()
end_month = months_data['interval'].dt.month.max() + 1
# generate list of datetime objects
month_dates = generate_month_dates(months_data, 'interval')
# inverse interval options dictionary
interval_options_inverse = { v:k for k,v in interval_options.items()}
#State and LGA dictionary
state_lga_dict = {
    state:{lga:lga for lga in sorted(months_data.loc[months_data.state == state,'lga_name'].unique())}
      for state in sorted(months_data['state'].unique())
      }
# inverse status labels
inv_var_labels = {v: k for k, v in var_labels.items()}

def generate_value_boxes(cpo_selected,df):
    # Dynamically generate value boxes based on categories in the DataFrame
    max_width = "420px"  # Adjust this as needed
    value_boxes = []
    for cpo in cpo_selected:
        cpos_in_lga = df.cpo_name.unique()
        if cpo in cpos_in_lga:
            icon_base64 = convert_image_to_base64(cpo_styles[cpo]['icon'])
            #cpo = clean_string(cpo)
            value_boxes.append(
                ui.div(
                    ui.value_box('',
                        ui.output_ui(f"output_{clean_string(cpo).lower().replace(' ', '_')}"),
                        showcase=ui.img(
                            src=f"data:image/png;base64,{icon_base64}", 
                            style = "width: 85px; padding: 0; margin: 0"
                        ),
                        theme = ui.value_box_theme(
                            fg = cpo_styles[cpo]['text'],
                            bg=cpo_styles[cpo]['fill']
                            ),
                        style="padding: 0; margin: 0; display: flex; align-items: left; justify-content: start; gap: 0;"  # Tight padding & alignment in value box
                        ),
                    style=f"max-width: {max_width}; padding: 1px; margin: 0;",  # External margin for box container
                    class_="gap-0"  # Applies smaller Bootstrap gap class
                )
            )
    return value_boxes

# ------------------------------------------------------------------------
# Define user interface
# ------------------------------------------------------------------------

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_slider("period",
                        "Select months",
                        min=start_month,
                        max=end_month,
                        value = [start_month,end_month],
                        step = 1,
                        ticks = True),
        ui.output_ui("ui_interval_select"),
        ui.input_select('lga_name',
                                    label = 'Select a local government area',
                                    choices = state_lga_dict,
                                    selected = next(iter(state_lga_dict))
                    ),
        ui.input_selectize("cpo_name",
                            label="Select Charge Point Operator",
                            choices=list(months_data['cpo_name'].unique()),  
                            selected=list(months_data['cpo_name'].unique()),
                            multiple=True
                            ),
        ui.output_ui('compute'),
        open="open",
    ),
    ui.layout_columns(
        ui.output_ui("value_boxes"),        
        # Unpack the list of value boxes
        fill=False,
        class_="gap-1",
    ),
    ui.card(
        ui.card_header(
            'Map and column graphs showing',
            ui.output_ui('card_header_heatmap'),
            ui.output_text('card_header_heatmap_lga'),
            ui.popover(icons["ellipsis"],ui.input_slider('threshold','Set threshold for utilisation',0,100,50),placement="top"),
            class_="d-flex align-items-center gap-1"
        ),
        ui.layout_columns(
            output_widget('chloropleth_map'),
            output_widget('column_graph'),
            full_screen=True,
            fill = True,
            class_ = "gap-2",
            col_widths = [6,6]
        ),        
        # This section applies gap-3 to space the cards horizontally
        class_="gap-2",  # Bootstrap gap class applied here
    ),
    title=ui.popover(
        [ui.h4(
            ui.div(
                ui.output_text("selected_period"),
                style="text-align: center;"  # Center text inside the div
                )
            ),
         fa.icon_svg("circle-info").add_class("ms-2"),
        ],
        ui.markdown('''
                    **Uptime**: the proportion of time the charger is in use and occupied or available for use.
                    **Utilisation**: the proportion of time the charger is charging, finishing or reserved.
                    **Unavailability**: the proportion of time the charger is unavailable or out of order.  
                    '''),
        placement='right'
    ),
     
    fillable=True,
    class_ = 'gap-1',
    style="padding: 2px; margin: 0px;"  # Reduces padding and removes outer margin of page_sidebar
)

# ------------------------------------------------------------------------
# Server logic
# ------------------------------------------------------------------------

def server(input: Inputs, output: Outputs, session: Session):
    
   # global  cpo_data_filtered,cpo_data_filtered_combined,cpo_data_filtered_prop,cpo_data_filtered_combined_prop 
    # Reactive value to store computed data
    cpo_data = reactive.Value(None)
    location_data = reactive.Value(None)
    postcode_data = reactive.Value(None)
    # Dictionary to store dynamically generated output functions
    dynamic_outputs = {}
    # Signal to track if compute() has completed
    compute_completed = reactive.Value(False)

      
    @render.ui
    @reactive.event(input.cpo_name,input.lga_name,input.period,input.selectize)
    def compute():
        # Reset completion flag and cpo_data_filtered
        compute_completed.set(False)
                
        with ui.Progress(min=1, max=2) as p:
            p.set(message="Calculation in progress", detail="This may take a while...")
            # Convert input.daterange() to datetime with UTC timezone
            selected = input.period()
            lga_name = input.lga_name()
            cpo_selected = input.cpo_name()
            start_date = pd.to_datetime(month_dates[selected[0]-1],utc = True)
            end_date = pd.to_datetime((month_dates[selected[1]-1] - pd.Timedelta(days=1)), utc = True)
            interval_option = input.selectize()
            
            # CPO, LGA, time period and interval filtered data
            # Filter across the selected time period using the converted dates
            mask1 = ((months_data['interval'] >= start_date) &
                    (months_data['interval'] < end_date) & 
                    (months_data['lga_name'] == lga_name) &
                    (months_data['cpo_name'].isin(cpo_selected)) 
                    )
            #Initial filter of data
            months_data_filtered = months_data.loc[mask1,:]
            # check for data
            if len(months_data_filtered) == 0:
                compute_completed.set(True)
                return ui.div("No data Available")
            # aggregate list 1 for cpo_data
            agg_list1 = ['cpo_name']
            #aggregate list 2 for location
            agg_list2 = ['cpo_name','address1','address2','postcode','latitude','longitude']
            #aggregate list 3 for postcode
            agg_list3 = ['postcode']
            data_list = []
            for i,agg_list in enumerate([agg_list1,agg_list2,agg_list3]):
                processed_data = process_data(months_data_filtered, agg_list, interval_option, combine_cols=True)
                p.set(i+1, message="Computing.. Aggregating on column list and time interval")
                data_list.append(processed_data)  
            # Mark compute as complete
            compute_completed.set(True)
            cpo_data.set(data_list[0])
            location_data.set(data_list[1])
            postcode_data.set(data_list[2])
            return 'Processing complete'
       
    @output
    @render.text
    def selected_period():
        # Get the selected range of months from the slider and convert to month names
        selected = input.period()
        start = month_dates[selected[0]-1].strftime('%d %B')
        end = (month_dates[selected[1]-1] - pd.Timedelta(days=1)).strftime('%d %B')
        return f"Charge point Utilisation Dashboard - {start} to {end}"
    
    @output
    @render.ui
    def card_header_heatmap():
        # Get the selected range of months from the slider and convert to month names
        return ui.input_select("status_prop", None, utilisation_status, width="auto"),   
    @output
    @render.text
    def card_header_heatmap_lga():
        lga_name = input.lga_name()
        return f"for {lga_name}."
    
    # Reactive function to update slider maximum based on the maximum value of df1[status_prop]
    @reactive.Effect
    def update_threshold_max():
        if not compute_completed.get():
            return None
        data1 = cpo_data.get()
        status_prop = input.status_prop()
        # Ensure df1 and status_prop are accessible
        max_value = data1[status_prop].mean()
        # Update the max value of the threshold slider
        ui.update_slider(
            'threshold',
            value=max_value # Keep current value within the new range
            )
    
    @output
    @render.ui
    def value_boxes():
        # Ensure compute() has completed before proceeding
        if not compute_completed.get():
            return ui.div("Data is still being computed...")
        # Dynamically generate value boxes based on selected CPOs
        # Generate value boxes based on `cpo_data_filtered_combined_prop`
        data = cpo_data.get()
        cpo_selected = input.cpo_name()  # Get the selected CPOs
        # Calculate column widths dynamically
        return ui.layout_columns(
            *generate_value_boxes(cpo_selected,data)
                        )  # Regenerate value boxes
    
    # Generate dynamic outputs for each CPO based on selection
    def create_output_func(cpo,interval_option, selected_period):
        
        output_name = f"output_{clean_string(cpo).lower().replace(' ', '_')}"
        
        @output(id=output_name)
        @render.text
        @reactive.event(input.cpo_name,input.lga_name,input.period,input.selectize)  # Trigger updates when `cpo` changes
        def output_text(cpo=cpo):
            data = cpo_data.get()
            # relevant Hourly stats
            average_uptime = data.loc[data.cpo_name == cpo,:].eval('in_use + Available').mean()
            minimum_uptime = data.loc[data.cpo_name == cpo,:].eval('in_use + Available').min()
            average_utilisation = data.loc[data.cpo_name == cpo,:].eval('in_use').mean()
            maximum_unavailability = data.loc[data.cpo_name == cpo,'unavailable_out_of_order'].max()
            average_unavailability = data.loc[data.cpo_name == cpo,'unavailable_out_of_order'].mean()
            evse_count = data.loc[data.cpo_name == cpo,'evse_port_site_count']
            period_duration =  selected_period[1] - selected_period[0]
            if (period_duration > 1) or (interval_option != 'ME'):
                return ui.div(
                    ui.HTML(
                        f"""
                        <div style="font-size: 0.4em; line-height: 1.1;">
                            <strong>{cpo}'s {interval_options[interval_option]} statistics</strong><br>
                            <strong>Number of chargers:</strong> {int(evse_count.max())} chargers<br>
                            <strong>Average Uptime:</strong> {average_uptime: .1f}% per {interval_options2[interval_option]}<br>
                            <strong>Minimum Uptime:</strong> {minimum_uptime: .1f}% per {interval_options2[interval_option]}<br>
                            <strong>Average Utilisation:</strong> {average_utilisation: .1f}% per {interval_options2[interval_option]}<br>
                            <strong>Maximum Unavailability:</strong> {maximum_unavailability: .1f}% per {interval_options2[interval_option]}<br>
                        </div>
                        """
                    ),
                    style = "display: flex; align-items: flex-start; padding: 0; margin: 0;"
                )
            elif (interval_option == 'ME') and (period_duration == 1):
                return ui.div(
                    ui.HTML(
                        f"""
                        <div style="font-size: 0.4em; line-height: 1.1;">
                            <strong>{cpo}'s {interval_options[interval_option]} statistics</strong><br>
                            <strong>Number of chargers:</strong> {int(evse_count.max())} chargers<br>
                            <strong>Uptime:</strong> {average_uptime: .1f}%<br>
                            <strong>Utilisation:</strong> {average_utilisation: .1f}%<br>
                            <strong>Unavailability:</strong> {maximum_unavailability: .1f}%<br>
                        </div>
                        """
                    ),
                    style = "display: flex; align-items: flex-start; padding: 0; margin: 0;"
                )               
            
        # Store in dynamic_outputs to keep a reference
        dynamic_outputs[output_name] = output_text        
    # Loop over unique CPOs and create dynamic output functions
    @reactive.Effect
    def dynamic_output_creation():
        if not compute_completed.get() or cpo_data.get() is None:
            return
        # Ensure compute has completed before proceeding
        interval_option = input.selectize()
        selected_period = input.period()
         # Clear any existing outputs
        dynamic_outputs.clear()
        # Create a unique output for each CPO in the selection
        for cpo in input.cpo_name():
            data = cpo_data.get()
            if cpo in data.cpo_name.unique():
                create_output_func(cpo,interval_option,selected_period)       
   
    @render.ui  
    @reactive.event(input.period)  
    def ui_interval_select():
        time_series_range  = end_month - start_month
        if time_series_range < 3:
            available_intervals = {k: v for k, v in interval_options.items() if k not in ['Q', 'Y']}
        else:
            available_intervals = interval_options
          
        return ui.input_selectize("selectize",
                                label = "Select an interval option below:",
                                choices = available_intervals,  
                                selected = "ME",
                                multiple= False
                                ) 
    # Render chloropleth map based on inputs
    @output
    @render_widget
    def chloropleth_map():
        status_prop = input.status_prop()
        lga_name = input.lga_name()   
        data2 = location_data.get()
        data1 = postcode_data.get()
        
        # Filter data based on selected cpo_name
        #filtered_data = lga_cpo_data_filtered_prop2[(lga_cpo_data_filtered_prop2['cpo_name'] == cpo_name) & # type: ignore
        #                                        (lga_cpo_data_filtered_prop2['interval'] == selected_interval)] # type: ignore
    
        # Filter data based on selected cpo_name
        #filtered_data = lga_cpo_data_filtered_prop1[(lga_cpo_data_filtered_prop1['cpo_name'] == cpo_name)]   # type: ignore
        # Format float columns as percentage to 1 decimal place (excluding 'interval' and 'Total')
        #for col in status_prop_cols:
        #    filtered_data[col] = filtered_data[col].apply(lambda x: round(x*100,1))
            # Create the choropleth map

        return plot_chloropleth_map(data1,
                                    data2,
                                    geodf_filter_poa,
                                    lga_geogcoord_dict,
                                    status_prop,
                                    lga_name,
                                    poa_suburb
                                    )
        
    @output
    @render_widget
    def column_graph():
        status_prop = input.status_prop()
        threshold = input.threshold()
        interval_option = input.selectize()
        selected_period = input.period()        
        data1 = cpo_data.get()
        
        return  plot_column_graph(data1,
                                  status_prop,
                                  threshold,
                                  interval_option,
                                  selected_period
                         )
     
# Call App() to combine app_ui and server() into an interactive app
app = App(app_ui, server, debug = True)