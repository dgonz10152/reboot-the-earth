"use client";
import { Search, Flame } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import { cn } from "@/lib/utils"

export function BurnAreasSidebar({
  areas,
  selectedAreaId,
  onSelectArea,
  sortBy,
  onSortChange,
  filterThreat,
  onFilterChange
}) {
  const [searchQuery, setSearchQuery] = useState("")

  const filteredAreas = areas.filter((area) => area.name.toLowerCase().includes(searchQuery.toLowerCase()))

  const getThreatColor = (level) => {
    if (level === 1) return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
    if (level === 2) return "bg-green-500/20 text-green-400 border-green-500/30"
    if (level === 3) return "bg-amber-500/20 text-amber-400 border-amber-500/30"
    if (level === 4) return "bg-orange-500/20 text-orange-400 border-orange-500/30"
    return "bg-red-500/20 text-red-400 border-red-500/30"
  }

  const getThreatLabel = (level) => {
    if (level === 1) return "Very Low"
    if (level === 2) return "Low"
    if (level === 3) return "Moderate"
    if (level === 4) return "High"
    return "Critical"
  }

  return (
    <div className="w-[400px] border-r border-border bg-card flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-orange-500/10">
            <Flame className="w-6 h-6 text-orange-500" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Burn Manager</h1>
            <p className="text-sm text-muted-foreground">Control & Monitor</p>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search areas..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-background border-border" />
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          <Select value={sortBy} onValueChange={(v) => onSortChange(v)}>
            <SelectTrigger className="flex-1 bg-background border-border">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="threat">Threat Level</SelectItem>
              <SelectItem value="date">Last Burn Date</SelectItem>
              <SelectItem value="name">Name</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filterThreat?.toString() || "all"}
            onValueChange={(v) => onFilterChange(v === "all" ? null : Number.parseInt(v))}>
            <SelectTrigger className="flex-1 bg-background border-border">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Threats</SelectItem>
              <SelectItem value="5">Critical (5)</SelectItem>
              <SelectItem value="4">High (4)</SelectItem>
              <SelectItem value="3">Moderate (3)</SelectItem>
              <SelectItem value="2">Low (2)</SelectItem>
              <SelectItem value="1">Very Low (1)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      {/* Areas List */}
      <div className="flex-1 overflow-y-auto">
        <Accordion type="single" collapsible className="w-full">
          {filteredAreas.map((area) => (
            <AccordionItem
              key={area.id}
              value={area.id}
              className={cn(
                "border-b border-border px-6",
                selectedAreaId === area.id && "bg-accent/50"
              )}>
              <AccordionTrigger className="hover:no-underline py-4">
                <div className="flex items-center justify-between w-full pr-2">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-foreground">{area.name}</span>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn("text-xs font-medium border", getThreatColor(area.threatLevel))}>
                    {area.threatLevel}
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="pb-4">
                <div className="space-y-3 pt-2">
                  {/* Threat Breakdown */}
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">Threat Breakdown</p>
                    <div className="grid grid-cols-2 gap-2">
                      <StatBadge label="Dryness" value={area.statistics.dryness} />
                      <StatBadge label="Fuel Load" value={area.statistics.fuelLoad} />
                      <StatBadge label="Wind" value={area.statistics.windSpeed} />
                      <StatBadge label="Vegetation" value={area.statistics.vegetationDensity} />
                    </div>
                  </div>

                  {/* Last Burn Date */}
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Last Burn Date</p>
                    <p className="text-sm text-foreground">
                      {new Date(area.lastBurnDate).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </p>
                  </div>

                  {/* Weather Forecast */}
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Weather Forecast</p>
                    <p className="text-sm text-foreground">{area.weatherForecast}</p>
                  </div>

                  {/* View on Map Button */}
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full mt-2 bg-transparent"
                    onClick={() => onSelectArea(area.id)}>
                    View on Map
                  </Button>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
      {/* Legend */}
      <div className="p-6 border-t border-border bg-card">
        <p className="text-xs font-medium text-muted-foreground mb-3">Threat Levels</p>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((level) => (
            <div key={level} className="flex items-center gap-2">
              <div
                className={cn("w-3 h-3 rounded-full", getThreatColor(level).split(" ")[0])} />
              <span className="text-xs text-foreground">
                {level} - {getThreatLabel(level)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatBadge({
  label,
  value
}) {
  const getColor = (val) => {
    if (val <= 2) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
    if (val === 3) return "bg-amber-500/10 text-amber-400 border-amber-500/20"
    return "bg-orange-500/10 text-orange-400 border-orange-500/20"
  }

  return (
    <div className={cn("px-2 py-1 rounded border text-xs", getColor(value))}>
      <div className="font-medium">{label}</div>
      <div className="font-semibold">{value}/5</div>
    </div>
  );
}
