"use client";

import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";

// Fix for default marker icons in Next.js
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
	iconRetinaUrl:
		"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
	iconUrl:
		"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
	shadowUrl:
		"https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

// Custom icon colors based on threat level
const getThreatColor = (threatLevel) => {
	if (threatLevel >= 5) return "#dc2626"; // red-600
	if (threatLevel >= 4) return "#ea580c"; // orange-600
	if (threatLevel >= 3) return "#f59e0b"; // amber-600
	if (threatLevel >= 2) return "#84cc16"; // lime-600
	return "#22c55e"; // green-600
};

const createCustomIcon = (color, isSelected) => {
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
			border: ${borderWidth}px solid ${isSelected ? "#ffffff" : "#ffffff"};
			box-shadow: 0 4px 12px rgba(0,0,0,0.25), 0 0 0 ${
				isSelected ? "8px" : "0px"
			} ${color}40;
			transition: all 0.3s ease;
			cursor: pointer;
		"></div>`,
		iconSize: [size, size],
		iconAnchor: [size / 2, size],
	});
};

// Component to handle map view updates when selected area changes
function MapViewUpdater({ center, zoom }) {
	const map = useMap();
	useEffect(() => {
		if (center) {
			map.setView(center, zoom);
		}
	}, [map, center, zoom]);
	return null;
}

export function BurnMap({ areas, selectedAreaId, onSelectArea }) {
	// Calculate map center from all areas
	const mapCenter = useMemo(() => {
		if (!areas || areas.length === 0) {
			return [34.0522, -118.2437]; // Default to LA area
		}
		const avgLat =
			areas.reduce((sum, area) => sum + area.coordinates.lat, 0) / areas.length;
		const avgLng =
			areas.reduce((sum, area) => sum + area.coordinates.lng, 0) / areas.length;
		return [avgLat, avgLng];
	}, [areas]);

	// Get selected area coordinates for centering
	const selectedArea = useMemo(() => {
		return areas?.find((area) => area.id === selectedAreaId);
	}, [areas, selectedAreaId]);

	// Determine zoom level and center
	const mapZoom = selectedArea ? 12 : 10;
	const centerPoint = selectedArea
		? [selectedArea.coordinates.lat, selectedArea.coordinates.lng]
		: mapCenter;

	if (!areas || areas.length === 0) {
		return (
			<div className="flex-1 bg-muted/30 flex items-center justify-center rounded-lg border border-border">
				<p className="text-muted-foreground">No burn areas to display</p>
			</div>
		);
	}

	// Only render map on client side
	if (typeof window === "undefined") {
		return (
			<div className="flex-1 bg-muted/30 flex items-center justify-center rounded-lg border border-border">
				<p className="text-muted-foreground">Loading map...</p>
			</div>
		);
	}

	return (
		<div className="flex-1 rounded-lg border border-border overflow-hidden shadow-lg">
			<MapContainer
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
					const color = getThreatColor(area.threatLevel);
					const icon = createCustomIcon(color, isSelected);

					return (
						<Marker
							key={area.id}
							position={[area.coordinates.lat, area.coordinates.lng]}
							icon={icon}
							eventHandlers={{
								click: () => {
									onSelectArea(area.id);
								},
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
												Threat Level:
											</span>
											<span
												className="text-xs font-semibold px-2 py-0.5 rounded-full"
												style={{
													backgroundColor: `${getThreatColor(area.threatLevel)}20`,
													color: getThreatColor(area.threatLevel),
												}}
											>
												{area.threatLevel}/5
											</span>
										</div>
										<p className="text-xs text-muted-foreground">
											<span className="font-medium">Region:</span> {area.region}
										</p>
										<p className="text-xs text-muted-foreground">
											<span className="font-medium">Last Burn:</span>{" "}
											{new Date(area.lastBurnDate).toLocaleDateString("en-US", {
												year: "numeric",
												month: "short",
												day: "numeric",
											})}
										</p>
									</div>
								</div>
							</Popup>
						</Marker>
					);
				})}
				<MapViewUpdater center={centerPoint} zoom={mapZoom} />
			</MapContainer>
		</div>
	);
}
