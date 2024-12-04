import React, {useState} from 'react';
import KpiSelector from '../KpiSelector/KpiSelector';
import Chart from '../Chart/Chart';
import {KPI} from "../../api/DataStructures";
import {simulateChartData} from "../../api/QuerySimulator";
import {Filter} from "../KpiSelector/FilterOptions";
import {TimeFrame} from "../KpiSelector/TimeSelector"
import PersistentDataManager from "../../api/PersistentDataManager";

const DataView: React.FC = () => {
    const dataManager = PersistentDataManager.getInstance();
    const [kpi, setKpi] = useState<KPI>(dataManager.getKpiList()[0]);
    const [timeFrame, setTimeFrame] = useState<TimeFrame>({from: new Date(), to: new Date(), aggregation: "hour"});
    const [graphType, setGraphType] = useState('pie');
    const [filters, setFilters] = useState<Filter>(new Filter('All', []));
    const [chartData, setChartData] = useState<any[]>([]);
    // Function to fetch chart data with applied filters

    const fetchChartData = async () => {
        const data = await simulateChartData(kpi, timeFrame, graphType, filters);
        setChartData(data);
    };

    return (
        <div className="flex-1 flex-col w-full h-full space-y-5 p-6 items-center">
            {/* KPI Selector and Generate Button */}
            <KpiSelector
                kpi={kpi}
                setKpi={setKpi}
                timeFrame={timeFrame}
                setTimeFrame={setTimeFrame}
                graphType={graphType}
                setGraphType={setGraphType}
                filters={filters}
                setFilters={setFilters}
                onGenerate={fetchChartData} // Fetch chart data when "Generate" button is clicked
            />

            {/* Chart Section */}
            <div className={` shadow-md p-5 bg-white flex w-auto`}>
                <Chart data={chartData} graphType={graphType} kpi={kpi} timeUnit={timeFrame.aggregation}/>
            </div>
        </div>
    );
};

export default DataView;