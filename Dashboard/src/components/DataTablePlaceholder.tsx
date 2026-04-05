import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Badge } from "./ui/badge";
import { MoreHorizontal, Download, Filter } from "lucide-react";

export function DataTablePlaceholder() {
  const mockData = [
    { 
      item: "Canned Beans", 
      category: "Canned Goods", 
      weight: "450 lbs", 
      expiration: "Jan 15, 2026",
      status: "Fresh",
      source: "Grocery Store"
    },
    { 
      item: "Fresh Apples", 
      category: "Fresh Produce", 
      weight: "125 lbs", 
      expiration: "Aug 12, 2025",
      status: "Urgent",
      source: "Individual Donor"
    },
    { 
      item: "Whole Wheat Bread", 
      category: "Grains/Bread", 
      weight: "89 lbs", 
      expiration: "Aug 14, 2025",
      status: "Soon",
      source: "Corporate Partner"
    },
    { 
      item: "Ground Beef (Frozen)", 
      category: "Protein/Meat", 
      weight: "200 lbs", 
      expiration: "Dec 20, 2025",
      status: "Fresh",
      source: "Government Program"
    },
    { 
      item: "Milk (1 Gallon)", 
      category: "Dairy Products", 
      weight: "156 lbs", 
      expiration: "Aug 10, 2025",
      status: "Urgent",
      source: "Grocery Store"
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Fresh":
        return "bg-green-100 text-green-800";
      case "Soon":
        return "bg-yellow-100 text-yellow-800";
      case "Urgent":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-gray-900">Current Inventory Status</h3>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm">
            <Filter className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm">
            <Download className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm">
            <MoreHorizontal className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
      <div className="border rounded">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Food Item</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Weight</TableHead>
              <TableHead>Expiration</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Source</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockData.map((row, index) => (
              <TableRow key={index}>
                <TableCell className="font-medium">{row.item}</TableCell>
                <TableCell>{row.category}</TableCell>
                <TableCell>{row.weight}</TableCell>
                <TableCell>{row.expiration}</TableCell>
                <TableCell>
                  <Badge className={getStatusColor(row.status)}>
                    {row.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-gray-600">{row.source}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}