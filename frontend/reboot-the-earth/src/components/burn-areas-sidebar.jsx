"use client";
import { Search, Flame } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { cn } from "@/lib/utils";

export function BurnAreasSidebar({
	areas,
	selectedAreaId,
	onSelectArea,
	sortBy,
	onSortChange,
	filterThreat,
	onFilterChange,
}) {
	const [searchQuery, setSearchQuery] = useState("");

	const filteredAreas = areas.filter((area) =>
		area.name.toLowerCase().includes(searchQuery.toLowerCase())
	);

	const getThreatColor = (level) => {
		// Normalize level to 0-10 scale if it's in 0-1 range
		const normalizedLevel = level < 1 ? level * 10 : level;
		if (normalizedLevel <= 2)
			return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
		if (normalizedLevel <= 4)
			return "bg-green-500/20 text-green-400 border-green-500/30";
		if (normalizedLevel <= 6)
			return "bg-amber-500/20 text-amber-400 border-amber-500/30";
		if (normalizedLevel <= 8)
			return "bg-orange-500/20 text-orange-400 border-orange-500/30";
		return "bg-red-500/20 text-red-400 border-red-500/30";
	};

	const getThreatLabel = (level) => {
		if (level === 1) return "Very Low";
		if (level === 2) return "Low";
		if (level === 3) return "Moderate";
		if (level === 4) return "High";
		return "Critical";
	};

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
					<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
					<Input
						placeholder="Search areas..."
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						className="pl-9 bg-background border-border"
					/>
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
						onValueChange={(v) =>
							onFilterChange(v === "all" ? null : Number.parseInt(v))
						}
					>
						<SelectTrigger className="flex-1 bg-background border-border">
							<SelectValue placeholder="Filter" />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="all">All Threats</SelectItem>
							<SelectItem value="10">Critical (10)</SelectItem>
							<SelectItem value="8">High (8-9)</SelectItem>
							<SelectItem value="6">Moderate (6-7)</SelectItem>
							<SelectItem value="4">Low (4-5)</SelectItem>
							<SelectItem value="2">Very Low (0-3)</SelectItem>
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
							value={String(area.id)}
							className={cn(
								"border-b border-border px-6",
								selectedAreaId === area.id && "bg-accent/50"
							)}
						>
							<AccordionTrigger className="hover:no-underline py-4">
								<div className="flex items-center justify-between w-full pr-2">
									<div className="flex items-center gap-3">
										<span className="text-sm font-medium text-foreground">
											{area.name}
										</span>
									</div>
									<Badge
										variant="outline"
										className={cn(
											"text-xs font-medium border",
											getThreatColor(area["calculated-threat-rating"])
										)}
									>
										{(() => {
											const rating = area["calculated-threat-rating"];
											const normalized = rating < 1 ? rating * 10 : rating;
											return normalized.toFixed(2);
										})()}
									</Badge>
								</div>
							</AccordionTrigger>
							<AccordionContent className="pb-4">
								<div className="space-y-3 pt-2">
									{/* Score */}
									<div>
										<p className="text-xs font-medium text-muted-foreground mb-1">
											Risk of Ignition
										</p>
										<StatBadge label={"Risk"} value={area["threat-rating"]} />
									</div>

									{/* Statistics */}
									<div className="space-y-2">
										<p className="text-xs font-medium text-muted-foreground">
											Risk Statistics
										</p>
										<div className="grid grid-cols-2 gap-2">
											<StatBadge label="Safety" value={area.statistics.safety} />
											<StatBadge
												label="Fire Behavior"
												value={area.statistics["fire-behavior"]}
											/>
											<StatBadge
												label="Resistance"
												value={area.statistics["resistance-to-containment"]}
											/>
											<StatBadge
												label="Ignition"
												value={area.statistics["ignition-procedures-and-methods"]}
											/>
											<StatBadge
												label="Duration"
												value={area.statistics["prescribed-fire-duration"]}
											/>
											<StatBadge
												label="Smoke Mgmt"
												value={area.statistics["smoke-management"]}
											/>
											<StatBadge
												label="Activities"
												value={area.statistics["number-and-dependence-of-activities"]}
											/>
											<StatBadge
												label="Organizations"
												value={area.statistics["management-organizations"]}
											/>
											<StatBadge
												label="Objectives"
												value={area.statistics["treatment-resource-objectives"]}
											/>
											<StatBadge label="Constraints" value={area.statistics.constraints} />
											<StatBadge
												label="Logistics"
												value={area.statistics["project-logistics"]}
											/>
										</div>
									</div>

									{/* Statistics */}
									<div className="space-y-2">
										<p className="text-xs font-medium text-muted-foreground">
											Risk Statistics
										</p>
										<div className="grid grid-cols-2 gap-2">
											<StatBadge
												label="Population"
												value={area["total-population"]}
												hide_10
											/>
											<StatBadge
												label="Monetary Value"
												value={area["total-value-estimate"]}
												hide_10
											/>
										</div>
									</div>

									{/* Feasibility Score */}
									<div>
										<p className="text-xs font-medium text-muted-foreground mb-1">
											Feasibility Score
										</p>
										<p className="text-sm text-foreground font-semibold">
											{(() => {
												const score = area["preliminary-feasability-score"];
												console.log(score);
												// Normalize from 0-1 to 1-10 scale: (value * 9) + 1
												const normalized = score < 1 ? score * 10 : score;
												return normalized.toFixed(2);
											})()}
											/10
										</p>
									</div>

									{/* Last Burn Date */}
									<div>
										<p className="text-xs font-medium text-muted-foreground mb-1">
											Last Burn Date
										</p>
										<p className="text-sm text-foreground">
											{new Date(area["last-burn-date"]).toLocaleDateString("en-US", {
												month: "short",
												day: "numeric",
												year: "numeric",
											})}
										</p>
									</div>

									{/* Weather */}
									<div>
										<p className="text-xs font-medium text-muted-foreground mb-1">
											Weather
										</p>
										<p className="text-sm text-foreground">
											{typeof area.weather === "string"
												? area.weather
												: area.weather?.daily
												? `Temp: ${
														area.weather.daily.temperature_2m_mean?.[0] || "N/A"
												  }°F, Wind: ${
														area.weather.daily.windspeed_10m_mean?.[0] || "N/A"
												  } mph`
												: "Weather data unavailable"}
										</p>
									</div>

									{/* Nearby Towns */}
									{area["nearby-towns"] && area["nearby-towns"].length > 0 && (
										<div>
											<p className="text-xs font-medium text-muted-foreground mb-1">
												Nearby Towns
											</p>
											<div className="space-y-1">
												{area["nearby-towns"].map((town, idx) => (
													<p key={idx} className="text-sm text-foreground">
														{town.name} ({town.population.toLocaleString()})
													</p>
												))}
											</div>
										</div>
									)}

									{/* View on Map Button */}
									<Button
										variant="outline"
										size="sm"
										className="w-full mt-2 bg-transparent"
										onClick={() => onSelectArea(area.id)}
									>
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
				<p className="text-xs font-medium text-muted-foreground mb-3">
					Threat Levels (0-10)
				</p>
				<div className="space-y-2">
					<div className="flex items-center gap-2">
						<div
							className={cn("w-3 h-3 rounded-full", getThreatColor(1).split(" ")[0])}
						/>
						<span className="text-xs text-foreground">0-2 - Very Low</span>
					</div>
					<div className="flex items-center gap-2">
						<div
							className={cn("w-3 h-3 rounded-full", getThreatColor(3).split(" ")[0])}
						/>
						<span className="text-xs text-foreground">3-4 - Low</span>
					</div>
					<div className="flex items-center gap-2">
						<div
							className={cn("w-3 h-3 rounded-full", getThreatColor(5).split(" ")[0])}
						/>
						<span className="text-xs text-foreground">5-6 - Moderate</span>
					</div>
					<div className="flex items-center gap-2">
						<div
							className={cn("w-3 h-3 rounded-full", getThreatColor(7).split(" ")[0])}
						/>
						<span className="text-xs text-foreground">7-8 - High</span>
					</div>
					<div className="flex items-center gap-2">
						<div
							className={cn("w-3 h-3 rounded-full", getThreatColor(9).split(" ")[0])}
						/>
						<span className="text-xs text-foreground">9-10 - Critical</span>
					</div>
				</div>
			</div>
		</div>
	);
}

function StatBadge({ label, value, hide_10 }) {
	// Convert value from 0-1 range to 0-10 range with 2 decimal places
	// If value is already in 0-10 range (>= 1), use it as-is
	const normalizedValue = value >= 1 ? value : value * 10;
	const displayValue = normalizedValue.toFixed(2);
	const numericValue = parseFloat(normalizedValue);

	const getColor = (val) => {
		if (val <= 4)
			return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
		if (val <= 6) return "bg-amber-500/10 text-amber-400 border-amber-500/20";
		return "bg-orange-500/10 text-orange-400 border-orange-500/20";
	};

	return (
		<div
			className={cn("px-2 py-1 rounded border text-xs", getColor(numericValue))}
		>
			<div className="font-medium">{label}</div>
			<div className="font-semibold">{displayValue + (hide_10 ? "" : "/10")}</div>
		</div>
	);
}
