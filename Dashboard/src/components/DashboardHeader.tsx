import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Search, Filter, Share, MoreHorizontal, User } from "lucide-react";

export function DashboardHeader() {
  return (
    <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      {/* Left section */}
      <div className="flex items-center gap-4">
        <div className="text-lg font-medium text-gray-800">Power BI Dashboard</div>
        <div className="text-sm text-gray-500">Workspace &gt; Sales Analytics</div>
      </div>
      
      {/* Center section */}
      <div className="flex items-center gap-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input 
            placeholder="Search dashboard..." 
            className="pl-10 w-64"
          />
        </div>
      </div>
      
      {/* Right section */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm">
          <Filter className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="sm">
          <Share className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="sm">
          <MoreHorizontal className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="sm">
          <User className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}