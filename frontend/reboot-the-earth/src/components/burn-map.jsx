"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";

const MapContainer = dynamic(
	() => import("react-leaflet").then((mod) => mod.MapContainer),
	{ ssr: false }
);
const TileLayer = dynamic(
	() => import("react-leaflet").then((mod) => mod.TileLayer),
	{ ssr: false }
);
const Marker = dynamic(
	() => import("react-leaflet").then((mod) => mod.Marker),
	{ ssr: false }
);
const Popup = dynamic(() => import("react-leaflet").then((mod) => mod.Popup), {
	ssr: false,
});

/**
 * Returns a color code based on the threat level.
 * @param {number} threatLevel - Threat level (0-10 scale, or 0-1 which will be normalized)
 * @returns {string} Hex color code for the threat level
 */
const getThreatColor = (threatLevel) => {
	const normalizedLevel = threatLevel < 1 ? threatLevel * 10 : threatLevel;
	if (normalizedLevel >= 8) return "#dc2626";
	if (normalizedLevel >= 6) return "#ea580c";
	if (normalizedLevel >= 4) return "#f59e0b";
	if (normalizedLevel >= 2) return "#84cc16";
	return "#22c55e";
};

/**
 * Map component displaying burn areas with threat level markers.
 * @param {Object} props - Component props
 * @param {Array} props.areas - Array of burn area objects
 * @param {string} props.selectedAreaId - ID of the currently selected area
 * @param {Function} props.onSelectArea - Callback function when an area is selected
 */
export function BurnMap({ areas, selectedAreaId, onSelectArea }) {
	const [leafletLoaded, setLeafletLoaded] = useState(false);
	const [L, setL] = useState(null);
	const [MapViewUpdater, setMapViewUpdater] = useState(null);

	useEffect(() => {
		if (typeof window !== "undefined") {
			Promise.all([import("leaflet"), import("react-leaflet")]).then(
				([leaflet, reactLeaflet]) => {
					const leafletModule = leaflet.default || leaflet;
					delete leafletModule.Icon.Default.prototype._getIconUrl;
					leafletModule.Icon.Default.mergeOptions({
						iconRetinaUrl:
							"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
						iconUrl:
							"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
						shadowUrl:
							"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
					});
					setL(leafletModule);

					const Updater = ({ center, zoom }) => {
						const map = reactLeaflet.useMap();
						useEffect(() => {
							if (center && map?.setView) {
								try {
									map.setView(center, zoom);
								} catch (error) {
									console.error("Error updating map view:", error);
								}
							}
						}, [map, center, zoom]);
						return null;
					};
					setMapViewUpdater(() => Updater);
					setLeafletLoaded(true);
				}
			);
		}
	}, []);

	const mapCenter = useMemo(() => {
		if (!areas?.length) {
			return [34.0522, -118.2437];
		}
		const avgLat =
			areas.reduce((sum, area) => sum + area.coordinates.lat, 0) / areas.length;
		const avgLng =
			areas.reduce((sum, area) => sum + area.coordinates.lng, 0) / areas.length;
		return [avgLat, avgLng];
	}, [areas]);

	const selectedArea = useMemo(() => {
		return areas?.find((area) => area.id === selectedAreaId);
	}, [areas, selectedAreaId]);

	const mapZoom = selectedArea ? 12 : 10;
	const centerPoint = selectedArea
		? [selectedArea.coordinates.lat, selectedArea.coordinates.lng]
		: mapCenter;

	/**
	 * Creates a custom Leaflet icon for markers.
	 * @param {string} color - Hex color code for the marker
	 * @param {boolean} isSelected - Whether the marker is currently selected
	 * @returns {Object|null} Leaflet icon object or null if creation fails
	 */
	const createCustomIcon = (color, isSelected) => {
		if (!L?.divIcon) return null;
		try {
			const size = isSelected ? 32 : 28;
			const borderWidth = isSelected ? 4 : 3;
			return L.divIcon({
				className: `custom-marker ${isSelected ? "selected" : ""}`,
				html: `<div style="
					background: linear-gradient(135deg, ${color} 0%, ${color}dd 100%);
					width: ${size}px;
					height: ${size}px;
					border-radius: 50% 50% 50% 0;
					transform: rotate(-45deg);
					border: ${borderWidth}px solid #ffffff;
					box-shadow: 0 4px 12px rgba(0,0,0,0.25), 0 0 0 ${
						isSelected ? "8px" : "0px"
					} ${color}40;
					transition: all 0.3s ease;
					cursor: pointer;
				"></div>`,
				iconSize: [size, size],
				iconAnchor: [size / 2, size],
			});
		} catch (error) {
			console.error("Error creating custom icon:", error);
			return null;
		}
	};

	if (!areas?.length) {
		return (
			<div className="flex-1 bg-muted/30 flex items-center justify-center rounded-lg border border-border">
				<p className="text-muted-foreground">No burn areas to display</p>
			</div>
		);
	}

	if (!leafletLoaded || typeof window === "undefined") {
		return (
			<div className="flex-1 bg-muted/30 flex items-center justify-center rounded-lg border border-border">
				<p className="text-muted-foreground">Loading map...</p>
			</div>
		);
	}

	return (
		<div className="flex-1 rounded-lg border border-border overflow-hidden shadow-lg">
			<MapContainer
				key={`map-${centerPoint[0]}-${centerPoint[1]}`}
				center={centerPoint}
				zoom={mapZoom}
				style={{ height: "100%", width: "100%", zIndex: 0 }}
				scrollWheelZoom={true}
				zoomControl={true}
			>
				<TileLayer
					attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
					url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
					subdomains="abcd"
				/>
				{areas.map((area) => {
					const isSelected = area.id === selectedAreaId;
					const threatRating = area["calculated-threat-rating"];
					const normalizedRating =
						threatRating < 1 ? threatRating * 10 : threatRating;
					const color = getThreatColor(normalizedRating);
					const icon = createCustomIcon(color, isSelected);

					if (!icon) return null;

					return (
						<Marker
							key={area.id}
							position={[area.coordinates.lat, area.coordinates.lng]}
							icon={icon}
							eventHandlers={{
								click: () => onSelectArea(area.id),
							}}
						>
							<Popup
								className="modern-popup"
								closeButton={true}
								autoClose={false}
								autoPan={true}
							>
								<div className="p-3 min-w-[200px]">
									<h3 className="font-semibold text-base mb-2 text-foreground">
										{area.name}
									</h3>
									<div className="space-y-1.5">
										<div className="flex items-center gap-2">
											<span className="text-xs font-medium text-muted-foreground">
												Threat Rating:
											</span>
											<span
												className="text-xs font-semibold px-2 py-0.5 rounded-full"
												style={{
													backgroundColor: `${color}20`,
													color: color,
												}}
											>
												{normalizedRating.toFixed(2)}/10
											</span>
										</div>
										<p className="text-xs text-muted-foreground">
											<span className="font-medium">Feasibility:</span>{" "}
											{(() => {
												const score = area["preliminary-feasability-score"];
												const normalized = score < 1 ? score * 9 + 1 : score;
												return normalized.toFixed(2);
											})()}
											/10
										</p>
										<p className="text-xs text-muted-foreground">
											<span className="font-medium">Last Burn:</span>{" "}
											{new Date(area["last-burn-date"]).toLocaleDateString("en-US", {
												year: "numeric",
												month: "short",
												day: "numeric",
											})}
										</p>
										{area["nearby-towns"]?.length > 0 && (
											<p className="text-xs text-muted-foreground">
												<span className="font-medium">Nearby:</span>{" "}
												{area["nearby-towns"].map((t) => t.name).join(", ")}
											</p>
										)}
									</div>
								</div>
							</Popup>
						</Marker>
					);
				})}
				{MapViewUpdater && <MapViewUpdater center={centerPoint} zoom={mapZoom} />}
			</MapContainer>
		</div>
	);
}
