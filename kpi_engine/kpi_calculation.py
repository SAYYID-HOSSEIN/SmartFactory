from kpi_dataframe_filter import kpi_dataframe_filter
from kpi_data_extraction import kpi_dataframe_data_extraction
import pandas as pd
import sympy

class kpi_engine:
    def energy_cost_savings(df, machine_id, time):
        fd = df
        fd = kpi_dataframe_filter.filter_dataframe_by_machine(fd, machine_id)
        fd = kpi_dataframe_filter.filter_dataframe_by_kpi(fd, 'cost')

        index = fd['time'].str.contains(time, na=False).idxmax()
        ## if index is the first of the dataframe there is no previous time measurement, return error
        return fd.at[fd.index[fd.index.get_loc(index) - 1], 'sum'] - fd.at[index, 'sum']

    def energy_cost_working_time(df, start_time, end_time):
        fd = df
        total_energy_cost = kpi_dataframe_data_extraction.sum_kpi(df=fd, kpi='cost_working', machine_id='all_machines', start_time=start_time, end_time=end_time)
        total_working_time = kpi_dataframe_filter.filter_dataframe_by_time(df=fd, start_time=start_time, end_time=end_time)['time'].nunique() * 24
        return  total_energy_cost / total_working_time

    def energy_cost_idle_time(df, start_time, end_time):
        fd = df
        total_energy_cost = kpi_dataframe_data_extraction.sum_kpi(df=fd, kpi='cost_idle', machine_id='all_machines', start_time=start_time, end_time=end_time)
        total_working_time = kpi_dataframe_data_extraction.sum_kpi(df=fd, kpi='working_time', machine_id='all_machines', start_time=start_time, end_time=end_time)
        return  total_energy_cost / total_working_time

    def energy_cost_per_unit(df, machine_id, start_time, end_time):
        fd = df
        total_working_cost = kpi_dataframe_data_extraction.sum_kpi(df=fd, kpi='cost_working', machine_id=machine_id, start_time=start_time, end_time=end_time)
        total_idle_cost = kpi_dataframe_data_extraction.sum_kpi(df=fd, kpi='cost_idle', machine_id=machine_id, start_time=start_time, end_time=end_time)
        return total_working_cost + total_idle_cost

    def power_consumption_efficiency(df, machine_id, start_time, end_time):
        fd = df
        total_working_time = kpi_dataframe_data_extraction.sum_kpi(kpi='working_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        total_power_consumption = kpi_dataframe_data_extraction.sum_kpi(df=fd, kpi='consumption', machine_id=machine_id, start_time=start_time, end_time=end_time)
        return total_working_time / total_power_consumption
        
    def power_consumption_trend(df, machine_id, start_previous_period, end_previous_period, start_current_period, end_current_period):
        fd = df
        if(not(end_previous_period < start_current_period)):
            print("bad chronological order")
        current_total_power_consumption = kpi_dataframe_data_extraction.sum_kpi(df=fd, kpi='consumption', machine_id=machine_id, start_time=start_current_period, end_time=end_current_period)
        previous_total_power_consumption = kpi_dataframe_data_extraction.sum_kpi(df=fd, kpi='consumption', machine_id=machine_id, start_time=start_previous_period, end_time=end_previous_period)
        return (current_total_power_consumption - previous_total_power_consumption) / previous_total_power_consumption

    def machine_utilization_rate(df, machine_id, start_time, end_time):
        fd = df
        total_working_time = kpi_dataframe_data_extraction.sum_kpi(kpi='working_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        total_idle_time = kpi_dataframe_data_extraction.sum_kpi(kpi='idle_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        total_offline_time = kpi_dataframe_data_extraction.sum_kpi(kpi='offline_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        return total_working_time / (total_working_time + total_idle_time + total_offline_time)

    def machine_usage_trend(df, machine_id, start_previous_period, end_previous_period, start_current_period, end_current_period):
        fd = df
        if(not(start_previous_period <= end_previous_period < start_current_period <= end_current_period)):
            print("bad chronological order")
        current_average_working_time = kpi_dataframe_data_extraction.avg_kpi(df=fd, kpi='working_time', machine_id=machine_id, start_time=start_current_period, end_time=end_current_period)
        previous_average_working_time = kpi_dataframe_data_extraction.avg_kpi(df=fd, kpi='working_time', machine_id=machine_id, start_time=start_previous_period, end_time=end_previous_period)
        return (current_average_working_time - previous_average_working_time) / previous_average_working_time

    '''
    def cost_per_unit():
        return -1

    def material_cost_per_unit():
        return -1

    def material_cost_per_unit():
        return -1
    '''

    def availability(df, machine_id, start_time, end_time):
        fd = df
        uptime = kpi_dataframe_data_extraction.sum_kpi(kpi='working_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        downtime = kpi_dataframe_data_extraction.sum_kpi(kpi='idle_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        return uptime / (uptime + downtime)

    def performance(df, machine_id, start_time, end_time):
        fd = df
        total_output = kpi_dataframe_data_extraction.sum_kpi(kpi='good_cycles', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        total_productive_time = kpi_dataframe_data_extraction.sum_kpi(kpi='working_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        return total_output / total_productive_time

    def throughput(df, machine_id, start_time, end_time):
        fd = df
        items_produced = kpi_dataframe_data_extraction.sum_kpi(kpi='good_cycles', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        time_employed = kpi_dataframe_data_extraction.sum_kpi(kpi='working_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time) + kpi_dataframe_data_extraction.sum_kpi(kpi='idle_time', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        return items_produced / time_employedz

    def quality(df, machine_id, start_time, end_time):
        fd = df
        good_work = kpi_dataframe_data_extraction.sum_kpi(kpi='good_cycles', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        bad_work = kpi_dataframe_data_extraction.sum_kpi(kpi='bad_cycles', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        total_work = good_work + bad_work
        return good_work / total_work

    def yield_fft(df, machine_id, start_time, end_time):
        fd = df
        defective_output = kpi_dataframe_data_extraction.sum_kpi(kpi='bad_cycles', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time)
        total_output = kpi_dataframe_data_extraction.sum_kpi(kpi='good_cycles', df=fd, machine_id=machine_id, start_time=start_time, end_time=end_time) + defective_output
        return (total_output - defective_output) / total_output

    '''
    def maintenance_cost():
        return -1

    def mean_time_between_failures():
        return -1

    def mean_time_between_maintenance():
        return -1

    def mean_time_to_repair():
        return -1
    '''

    def dynamic_kpi(df, machine_id, machine_type, start_time, end_time, kpi_id):
        # kpi_formula = extract formula through API and kpi_id
        formula = 'working_time_sum / (idle_time_sum + working_time_sum)'
        expr = sympy.parse_expr(formula)
        print(expr.free_symbols)
        # formula parsing
        # filtering (by time period, machine_id, etc)
        # data extraction
        # formula evaluation
        return