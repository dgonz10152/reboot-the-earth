"use client";
import { useState, useEffect } from "react";
import { BurnAreasSidebar } from "@/components/burn-areas-sidebar";
import { BurnMap } from "@/components/burn-map";
import { getData } from "@/lib/get-data";

// Import Mock Data
const mockBurnAreas = require("./mock-data.json");

export default function DashboardPage() {
	const [burnAreas, setBurnAreas] = useState(mockBurnAreas);
	const [selectedAreaId, setSelectedAreaId] = useState(null);
	const [sortBy, setSortBy] = useState("threat");
	const [filterThreat, setFilterThreat] = useState(null);

	useEffect(() => {
		const fetchBurnAreas = async () => {
			const data = await getData("/dummy");
			const real_data = data.data.regions;

			console.log(real_data);
			setBurnAreas(real_data);
		};
		fetchBurnAreas();
	}, []);
	// Sort and filter burn areas
	const filteredAndSortedAreas = burnAreas
		.filter((area) => (filterThreat ? area.threatLevel === filterThreat : true))
		.sort((a, b) => {
			if (sortBy === "threat") {
				return b.threatLevel - a.threatLevel;
			} else if (sortBy === "date") {
				return (
					new Date(b.lastBurnDate).getTime() - new Date(a.lastBurnDate).getTime()
				);
			} else {
				return a.name.localeCompare(b.name);
			}
		});

	const selectedArea = selectedAreaId
		? burnAreas.find((area) => area.id === selectedAreaId)
		: null;

	return (
		<div className="flex h-screen bg-background">
			<BurnAreasSidebar
				areas={filteredAndSortedAreas}
				selectedAreaId={selectedAreaId}
				onSelectArea={setSelectedAreaId}
				sortBy={sortBy}
				onSortChange={setSortBy}
				filterThreat={filterThreat}
				onFilterChange={setFilterThreat}
			/>
			<BurnMap
				areas={burnAreas}
				selectedAreaId={selectedAreaId}
				onSelectArea={setSelectedAreaId}
			/>
		</div>
	);
}
