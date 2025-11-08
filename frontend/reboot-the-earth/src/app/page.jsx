"use client";
import { useState, useEffect } from "react";
import { BurnAreasSidebar } from "@/components/burn-areas-sidebar";
import { BurnMap } from "@/components/burn-map";
import { getData } from "@/lib/get-data";

// Import Mock Data

export default function DashboardPage() {
	const [burnAreas, setBurnAreas] = useState([]);
	const [selectedAreaId, setSelectedAreaId] = useState(null);
	const [sortBy, setSortBy] = useState("threat");
	const [filterThreat, setFilterThreat] = useState(null);

	useEffect(() => {
		const fetchBurnAreas = async () => {
			try {
				// Add timestamp to bust cache
				const timestamp = Date.now();
				const data = await getData(`/v1?t=${timestamp}`);

				console.log("API Response:", data);
				// Backend returns: { status: "success", data: [...] }
				const real_data = data?.data || data?.regions || data;

				console.log("Extracted data:", real_data);
				// Ensure we have an array before setting state
				if (Array.isArray(real_data) && real_data.length > 0) {
					setBurnAreas(real_data);
				} else {
					console.warn("API returned invalid data structure, using mock data");
				}
			} catch (error) {
				console.error(
					"Failed to fetch burn areas from API, using mock data:",
					error
				);
				// Keep using mock data that's already in state
			}
		};
		fetchBurnAreas();
	}, []);
	// Sort and filter burn areas
	const filteredAndSortedAreas = (burnAreas || [])
		.filter((area) => {
			if (!filterThreat) return true;
			// Normalize threat rating to 0-10 scale for comparison
			const rating = area["calculated-threat-rating"];
			const normalized = rating < 1 ? rating * 10 : rating;
			// Filter by threshold ranges
			if (filterThreat === 10) return normalized >= 9.5;
			if (filterThreat === 8) return normalized >= 8 && normalized < 9.5;
			if (filterThreat === 6) return normalized >= 6 && normalized < 8;
			if (filterThreat === 4) return normalized >= 4 && normalized < 6;
			if (filterThreat === 2) return normalized < 4;
			return false;
		})
		.sort((a, b) => {
			if (sortBy === "threat") {
				const aRating = a["calculated-threat-rating"];
				const bRating = b["calculated-threat-rating"];
				const aNormalized = aRating < 1 ? aRating * 10 : aRating;
				const bNormalized = bRating < 1 ? bRating * 10 : bRating;
				return bNormalized - aNormalized;
			} else if (sortBy === "date") {
				return (
					new Date(b["last-burn-date"]).getTime() -
					new Date(a["last-burn-date"]).getTime()
				);
			} else {
				return a.name.localeCompare(b.name);
			}
		});

	const selectedArea =
		selectedAreaId && burnAreas
			? burnAreas.find((area) => area.id === selectedAreaId)
			: null;

	console.log("BUUURN", burnAreas);

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
				areas={burnAreas || []}
				selectedAreaId={selectedAreaId}
				onSelectArea={setSelectedAreaId}
			/>
		</div>
	);
}
