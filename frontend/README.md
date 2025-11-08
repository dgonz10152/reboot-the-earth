# FRONTEND

Next.js React application for visualizing wildfire risk data.

## Setup

### Prerequisites

- Node.js 18.x or higher
- npm or yarn package manager

### Installation

1. Navigate to the frontend directory:

   ```bash
   cd frontend/reboot-the-earth
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

## Environment Variables

Create a `.env.local` file in the `frontend/reboot-the-earth` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
# or
API_URL=http://localhost:5000
```

### API URL Configuration

The frontend uses the following environment variables (in order of precedence):

1. `NEXT_PUBLIC_API_URL` - Public API URL (exposed to browser)
2. `API_URL` - Fallback API URL

**Note**: If neither is set, the application will throw an error. Make sure to set at least one of these variables.

## Running the Development Server

Start the Next.js development server:

```bash
npm run dev
# or
yarn dev
```

The application will be available at `http://localhost:3000`.

## Building for Production

Build the production-ready application:

```bash
npm run build
# or
yarn build
```

Start the production server:

```bash
npm start
# or
yarn start
```

## Dependencies

### Core Dependencies

- **next**: React framework for production
- **react**: React library
- **react-dom**: React DOM renderer
- **leaflet**: Interactive maps library
- **react-leaflet**: React components for Leaflet maps
- **lucide-react**: Icon library
- **@radix-ui/react-accordion**: Accessible accordion component
- **@radix-ui/react-select**: Accessible select component
- **class-variance-authority**: Component variant management
- **clsx**: Utility for constructing className strings
- **tailwind-merge**: Merge Tailwind CSS classes

### Development Dependencies

- **tailwindcss**: Utility-first CSS framework
- **eslint**: JavaScript linter
- **babel-plugin-react-compiler**: React compiler plugin

## Project Structure

```
frontend/reboot-the-earth/
├── src/
│   ├── app/
│   │   ├── page.jsx          # Main page component
│   │   ├── layout.js         # Root layout
│   │   └── globals.css       # Global styles
│   ├── components/
│   │   ├── burn-map.jsx      # Map visualization component
│   │   ├── burn-areas-sidebar.jsx  # Sidebar component
│   │   └── ui/               # UI components (accordion, badge, button, etc.)
│   └── lib/
│       ├── get-data.js       # API data fetching utility
│       └── utils.js          # Utility functions
├── public/                   # Static assets
├── package.json              # Dependencies and scripts
└── .env.local                # Environment variables (create this)
```

## API Integration

The frontend fetches data from the backend API using the `get-data.js` utility:

- **Endpoint**: Configured via `NEXT_PUBLIC_API_URL` or `API_URL`
- **Caching**: Explicitly disabled (no-store cache policy)
- **Error Handling**: Throws error if API URL is not configured

## Features

- Interactive map visualization using Leaflet
- Real-time wildfire risk data display
- Responsive sidebar with burn area information
- Modern UI built with Tailwind CSS and Radix UI components

## Notes

- The frontend requires the backend server to be running
- API calls are made to the backend endpoints (`/v0` and `/v1`)
- Map tiles are loaded from Leaflet's default tile provider
- The application uses Next.js 16 with React 19
