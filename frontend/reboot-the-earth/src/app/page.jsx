"use client";
import { useState, useEffect } from "react";
import { BurnAreasSidebar } from "@/components/burn-areas-sidebar";
import { BurnMap } from "@/components/burn-map";
import { getData } from "@/lib/get-data";

/**
 * Normalizes threat rating to a 0-10 scale for consistent comparison.
 * @param {number} rating - The threat rating value
 * @returns {number} Normalized rating on 0-10 scale
 */
const normalizeThreatRating = (rating) => {
	return rating < 1 ? rating * 10 : rating;
};

/**
 * Main dashboard page component for displaying and managing burn areas.
 * Fetches burn area data, provides filtering and sorting capabilities,
 * and renders both a sidebar list and interactive map view.
 *
 * @returns {JSX.Element} Dashboard layout with sidebar and map components
 */
export default function DashboardPage() {
	const [burnAreas, setBurnAreas] = useState([]);
	const [selectedAreaId, setSelectedAreaId] = useState(null);
	const [sortBy, setSortBy] = useState("threat");
	const [filterThreat, setFilterThreat] = useState(null);

	useEffect(() => {
		const fetchBurnAreas = async () => {
			try {
				const data = await getData(`/v1?t=${Date.now()}`);
				const areas = data?.data || data?.regions || data;

				if (Array.isArray(areas) && areas.length > 0) {
					setBurnAreas(areas);
				}
			} catch (error) {
				console.error("Failed to fetch burn areas:", error);
			}
		};
		fetchBurnAreas();
	}, []);

	const filteredAndSortedAreas = (burnAreas || [])
		.filter((area) => {
			if (!filterThreat) return true;

			const normalized = normalizeThreatRating(area["calculated-threat-rating"]);

			if (filterThreat === 10) return normalized >= 9.5;
			if (filterThreat === 8) return normalized >= 8 && normalized < 9.5;
			if (filterThreat === 6) return normalized >= 6 && normalized < 8;
			if (filterThreat === 4) return normalized >= 4 && normalized < 6;
			if (filterThreat === 2) return normalized < 4;
			return false;
		})
		.sort((a, b) => {
			if (sortBy === "threat") {
				const aNormalized = normalizeThreatRating(a["calculated-threat-rating"]);
				const bNormalized = normalizeThreatRating(b["calculated-threat-rating"]);
				return bNormalized - aNormalized;
			}

			if (sortBy === "date") {
				return (
					new Date(b["last-burn-date"]).getTime() -
					new Date(a["last-burn-date"]).getTime()
				);
			}

			return a.name.localeCompare(b.name);
		});

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
