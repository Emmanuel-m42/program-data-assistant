declare global {
	/** API base URL baked in at build time, or "demo" for the recorded runs. */
	const __API_URL__: string;
	namespace App {}
}

export {};
