import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { MoreHorizontal, BarChart3, PieChart, LineChart, TrendingUp } from "lucide-react";

interface ChartPlaceholderProps {
  title: string;
  type: "bar" | "line" | "pie" | "area" | "table";
  height?: string;
}

function ChartPlaceholder({ title, type, height = "h-64" }: ChartPlaceholderProps) {
  const getIcon = () => {
    switch (type) {
      case "bar":
        return <BarChart3 className="w-8 h-8" />;
      case "line":
        return <LineChart className="w-8 h-8" />;
      case "pie":
        return <PieChart className="w-8 h-8" />;
      case "area":
        return <TrendingUp className="w-8 h-8" />;
      default:
        return <BarChart3 className="w-8 h-8" />;
    }
  };

  return (
    <Card className={`p-4 ${height}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-gray-900">{title}</h3>
        <Button variant="ghost" size="sm">
          <MoreHorizontal className="w-4 h-4" />
        </Button>
      </div>
      
      <div className="flex-1 flex items-center justify-center text-gray-400 bg-gray-50 rounded border-2 border-dashed border-gray-200 h-full">
        <div className="text-center">
          {getIcon()}
          <p className="text-sm mt-2 capitalize">{type} Chart Placeholder</p>
        </div>
      </div>
    </Card>
  );
}

export function ChartPlaceholders() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      <ChartPlaceholder title="Food Distribution by Category (lbs)" type="bar" />
      <ChartPlaceholder title="Monthly Inventory Trends" type="line" />
      <ChartPlaceholder title="Food Source Distribution" type="pie" />
      <ChartPlaceholder title="Expiration Timeline (Next 30 Days)" type="area" />
    </div>
  );
}