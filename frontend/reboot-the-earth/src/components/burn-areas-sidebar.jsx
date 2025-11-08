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

/**
 * Normalizes a value from 0-1 scale to 0-10 scale if needed.
 * @param {number} value - The value to normalize
 * @returns {number} Normalized value on 0-10 scale
 */
const normalizeToTen = (value) => (value < 1 ? value * 10 : value);

/**
 * Returns Tailwind CSS classes for threat level colors based on a 0-10 scale.
 * @param {number} level - Threat level (0-10 scale)
 * @returns {string} Tailwind CSS classes for the threat level color
 */
const getThreatColor = (level) => {
	const normalizedLevel = normalizeToTen(level);
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

/**
 * Sidebar component for displaying and managing burn areas.
 * @param {Object} props - Component props
 * @param {Array<Object>} props.areas - Array of burn area objects
 * @param {string|number} props.selectedAreaId - ID of the currently selected area
 * @param {Function} props.onSelectArea - Callback when an area is selected
 * @param {string} props.sortBy - Current sort option ("threat", "date", "name")
 * @param {Function} props.onSortChange - Callback when sort option changes
 * @param {number|null} props.filterThreat - Current threat level filter (null for all)
 * @param {Function} props.onFilterChange - Callback when threat filter changes
 * @returns {JSX.Element} The sidebar component
 */
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

	return (
		<div className="w-[400px] border-r border-border bg-card flex flex-col h-full">
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

				<div className="relative mb-4">
					<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
					<Input
						placeholder="Search areas..."
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						className="pl-9 bg-background border-border"
					/>
				</div>

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
										{normalizeToTen(area["calculated-threat-rating"]).toFixed(2)}
									</Badge>
								</div>
							</AccordionTrigger>
							<AccordionContent className="pb-4">
								<div className="space-y-3 pt-2">
									<div>
										<p className="text-xs font-medium text-muted-foreground mb-1">
											Risk of Ignition
										</p>
										<StatBadge label="Risk" value={area["threat-rating"]} />
									</div>

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

									<div className="space-y-2">
										<p className="text-xs font-medium text-muted-foreground">
											Additional Information
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

									<div>
										<p className="text-xs font-medium text-muted-foreground mb-1">
											Feasibility Score
										</p>
										<p className="text-sm text-foreground font-semibold">
											{normalizeToTen(area["preliminary-feasability-score"]).toFixed(2)}/10
										</p>
									</div>

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

/**
 * Displays a statistic badge with normalized value and color coding.
 * @param {Object} props - Component props
 * @param {string} props.label - Label text for the statistic
 * @param {number} props.value - Statistic value (0-1 or 0-10 scale)
 * @param {boolean} [props.hide_10] - If true, omits "/10" suffix from display
 * @returns {JSX.Element} The statistic badge component
 */
function StatBadge({ label, value, hide_10 }) {
	const normalizedValue = normalizeToTen(value);
	const displayValue = normalizedValue.toFixed(2);

	const getColor = (val) => {
		if (val <= 4)
			return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
		if (val <= 6) return "bg-amber-500/10 text-amber-400 border-amber-500/20";
		return "bg-orange-500/10 text-orange-400 border-orange-500/20";
	};

	return (
		<div
			className={cn("px-2 py-1 rounded border text-xs", getColor(normalizedValue))}
		>
			<div className="font-medium">{label}</div>
			<div className="font-semibold">{displayValue + (hide_10 ? "" : "/10")}</div>
		</div>
	);
}
