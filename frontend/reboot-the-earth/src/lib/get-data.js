/**
 * Fetches data from an API endpoint and returns the parsed JSON response
 * Works in both Next.js server and client components
 * @param {string} endpoint - The API endpoint path (e.g., '/burn-areas') or full URL
 * @param {RequestInit} options - Optional fetch options (method, headers, body, etc.)
 * @returns {Promise<Object>} - The parsed JSON response as an object
 * @throws {Error} - If the request fails or response is not valid JSON
 */
export async function getData(endpoint = "", options = {}) {
	// In Next.js, NEXT_PUBLIC_* variables are available in both server and client
	// API_URL (without prefix) is only available server-side
	const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL;

	if (!apiUrl) {
		const isClient = typeof window !== "undefined";
		const envVarName = isClient
			? "NEXT_PUBLIC_API_URL"
			: "API_URL or NEXT_PUBLIC_API_URL";
		throw new Error(
			`${envVarName} environment variable is not set. Please add it to your .env.local file.`
		);
	}

	// Construct full URL - if endpoint starts with http, use it as-is, otherwise append to base URL
	const fullUrl = endpoint.startsWith("http")
		? endpoint
		: `${apiUrl.replace(/\/$/, "")}/${endpoint.replace(/^\//, "")}`;

	try {
		const response = await fetch(fullUrl, {
			...options,
			headers: {
				"Content-Type": "application/json",
				...options.headers,
			},
		});

		if (!response.ok) {
			throw new Error(
				`API request failed: ${response.status} ${response.statusText}`
			);
		}

		const data = await response.json();
		return data;
	} catch (error) {
		if (error instanceof SyntaxError) {
			throw new Error(`Failed to parse JSON response: ${error.message}`);
		}
		throw error;
	}
}
