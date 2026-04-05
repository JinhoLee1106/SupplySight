import { Card } from "./ui/card";
import { TrendingUp, TrendingDown, Scale, Users, Package, AlertTriangle } from "lucide-react";

interface KPICardProps {
  title: string;
  value: string;
  change: string;
  trend: "up" | "down";
  icon: React.ReactNode;
}

function KPICard({ title, value, change, trend, icon }: KPICardProps) {
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
          <div className={`flex items-center gap-1 mt-2 text-sm ${
            trend === "up" ? "text-green-600" : "text-red-600"
          }`}>
            {trend === "up" ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span>{change}</span>
          </div>
        </div>
        <div className="text-gray-400">
          {icon}
        </div>
      </div>
    </Card>
  );
}

export function KPICards() {
  const kpiData = [
    {
      title: "Total Food Inventory",
      value: "24,850 lbs",
      change: "+1,200 lbs",
      trend: "up" as const,
      icon: <Scale className="w-8 h-8" />
    },
    {
      title: "Families Served This Month",
      value: "1,847",
      change: "+127 families",
      trend: "up" as const,
      icon: <Users className="w-8 h-8" />
    },
    {
      title: "Food Distributed (30 days)",
      value: "18,240 lbs",
      change: "+2,150 lbs",
      trend: "up" as const,
      icon: <Package className="w-8 h-8" />
    },
    {
      title: "Days of Supply Remaining",
      value: "12 days",
      change: "-2 days",
      trend: "down" as const,
      icon: <AlertTriangle className="w-8 h-8" />
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
      {kpiData.map((kpi, index) => (
        <KPICard key={index} {...kpi} />
      ))}
    </div>
  );
}