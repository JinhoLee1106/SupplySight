import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Checkbox } from "./ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Slider } from "./ui/slider";
import { Calendar, ChevronDown, X } from "lucide-react";

export function FilterSidebar() {
  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-700">Filters</h3>
        <Button variant="ghost" size="sm">
          <X className="w-4 h-4" />
        </Button>
      </div>
      
      {/* Date Range Filter */}
      <Card className="p-3 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <Calendar className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium">Date Range</span>
        </div>
        <Select>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="last7">Last 7 days</SelectItem>
            <SelectItem value="last30">Last 30 days</SelectItem>
            <SelectItem value="last90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </Card>
      
      {/* Food Category Filter */}
      <Card className="p-3 mb-4">
        <div className="text-sm font-medium mb-2">Food Categories</div>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Checkbox id="canned" />
            <label htmlFor="canned" className="text-sm">Canned Goods</label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox id="fresh" />
            <label htmlFor="fresh" className="text-sm">Fresh Produce</label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox id="dairy" />
            <label htmlFor="dairy" className="text-sm">Dairy Products</label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox id="protein" />
            <label htmlFor="protein" className="text-sm">Protein/Meat</label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox id="grains" />
            <label htmlFor="grains" className="text-sm">Grains/Bread</label>
          </div>
        </div>
      </Card>
      
      {/* Expiration Status */}
      <Card className="p-3 mb-4">
        <div className="text-sm font-medium mb-2">Expiration Status</div>
        <Select>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="All items" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="fresh">Fresh (30+ days)</SelectItem>
            <SelectItem value="soon">Expires Soon (7-30 days)</SelectItem>
            <SelectItem value="urgent">Urgent (1-7 days)</SelectItem>
            <SelectItem value="expired">Expired</SelectItem>
          </SelectContent>
        </Select>
      </Card>
      
      {/* Donation Source */}
      <Card className="p-3 mb-4">
        <div className="text-sm font-medium mb-2">Donation Source</div>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Checkbox id="grocery" />
            <label htmlFor="grocery" className="text-sm">Grocery Stores</label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox id="individual" />
            <label htmlFor="individual" className="text-sm">Individual Donors</label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox id="corporate" />
            <label htmlFor="corporate" className="text-sm">Corporate Partners</label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox id="government" />
            <label htmlFor="government" className="text-sm">Government Programs</label>
          </div>
        </div>
      </Card>
      
      {/* Weight Range */}
      <Card className="p-3">
        <div className="text-sm font-medium mb-2">Weight Range (lbs)</div>
        <Slider
          defaultValue={[500]}
          max={5000}
          min={0}
          step={100}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>0 lbs</span>
          <span>5,000 lbs</span>
        </div>
      </Card>
    </div>
  );
}