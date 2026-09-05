import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import client from '../api/client'

// Fix Leaflet default marker icons
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Custom icons
const vehicleIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
})

const stoppageIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
})

// All timestamps stored as UTC in DB
// Append 'Z' so JS treats them as UTC, then display in IST
const toIST = (timeStr) => {
    if (!timeStr) return 'Unknown'
    const utcStr = timeStr.endsWith('Z') ? timeStr : timeStr + 'Z'
    return new Date(utcStr)
}

const formatTime = (timeStr) => {
    if (!timeStr) return 'Unknown'
    const utcStr = timeStr.endsWith('Z') ? timeStr : timeStr + 'Z'
    return new Date(utcStr).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit'
    })
}

const formatDateTime = (timeStr) => {
    if (!timeStr) return 'Unknown'
    const utcStr = timeStr.endsWith('Z') ? timeStr : timeStr + 'Z'
    return new Date(utcStr).toLocaleString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })
}

const formatDuration = (seconds) => {
    if (!seconds) return 'Unknown'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
}

export default function Dashboard({ onLogout }) {
    const [vehicles, setVehicles] = useState([])
    const [stoppages, setStoppages] = useState([])
    const [tripPath, setTripPath] = useState([])
    const [selectedStoppage, setSelectedStoppage] = useState(null)
    const [loading, setLoading] = useState(true)
    const [totalStoppages, setTotalStoppages] = useState(0)

    useEffect(() => {
        fetchData()
    }, [])

    const fetchData = async () => {
        try {
            const [vehiclesRes, stoppagesRes, pathRes] = await Promise.all([
                client.get('/api/v1/vehicles'),
                client.get('/api/v1/stoppages'),
                client.get('/api/v1/trip-path')
            ])
            setVehicles(vehiclesRes.data)
            setStoppages(stoppagesRes.data.data)
            setTotalStoppages(stoppagesRes.data.total)
            setTripPath(pathRes.data)
        } catch (err) {
            console.error('Failed to fetch data:', err)
        } finally {
            setLoading(false)
        }
    }

    // Map center — Bengaluru
    const mapCenter = [12.9086, 77.5437]
    const pathPositions = tripPath.map(p => [p.lat, p.lng])

    return (
        <div style={{ display: 'flex', height: '100vh', background: '#0f172a' }}>

            {/* Sidebar */}
            <div style={{
                width: '320px',
                background: '#1e293b',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                borderRight: '1px solid #334155'
            }}>
                {/* Header */}
                <div style={{
                    padding: '20px',
                    borderBottom: '1px solid #334155'
                }}>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                    }}>
                        <div>
                            <h1 style={{
                                color: '#f8fafc',
                                fontSize: '16px',
                                fontWeight: '700',
                                margin: 0
                            }}>
                                Fleet Monitor
                            </h1>
                            <p style={{
                                color: '#64748b',
                                fontSize: '11px',
                                margin: '2px 0 0'
                            }}>
                                Stoppage Detection System
                            </p>
                        </div>
                        <button
                            onClick={onLogout}
                            style={{
                                background: 'transparent',
                                border: '1px solid #334155',
                                color: '#94a3b8',
                                padding: '6px 12px',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '12px'
                            }}
                        >
                            Logout
                        </button>
                    </div>
                </div>

                {/* Stats */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '1px',
                    background: '#334155',
                    borderBottom: '1px solid #334155'
                }}>
                    {[
                        { label: 'Vehicles', value: vehicles.length },
                        { label: 'Stoppages', value: stoppages.length },
                        { label: 'Total Stoppages', value: totalStoppages },
                    ].map(stat => (
                        <div key={stat.label} style={{
                            background: '#1e293b',
                            padding: '16px',
                            textAlign: 'center'
                        }}>
                            <div style={{
                                color: '#3b82f6',
                                fontSize: '24px',
                                fontWeight: '700'
                            }}>
                                {stat.value}
                            </div>
                            <div style={{
                                color: '#64748b',
                                fontSize: '11px',
                                marginTop: '2px'
                            }}>
                                {stat.label}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Vehicles */}
                <div style={{ padding: '16px 20px 8px' }}>
                    <p style={{
                        color: '#64748b',
                        fontSize: '11px',
                        fontWeight: '600',
                        letterSpacing: '0.05em',
                        margin: 0
                    }}>
                        VEHICLES
                    </p>
                </div>

                {vehicles.map(v => (
                    <div key={v.id} style={{
                        padding: '10px 20px',
                        borderBottom: '1px solid #0f172a'
                    }}>
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}>
                            <div style={{
                                width: '8px',
                                height: '8px',
                                borderRadius: '50%',
                                background: '#22c55e'
                            }} />
                            <span style={{
                                color: '#f8fafc',
                                fontSize: '13px',
                                fontWeight: '500'
                            }}>
                                {v.name}
                            </span>
                        </div>
                        <p style={{
                            color: '#64748b',
                            fontSize: '11px',
                            margin: '3px 0 0 16px'
                        }}>
                            Last seen: {formatDateTime(v.last_seen)}
                        </p>
                    </div>
                ))}

                {/* Stoppages */}
                <div style={{ padding: '16px 20px 8px' }}>
                    <p style={{
                        color: '#64748b',
                        fontSize: '11px',
                        fontWeight: '600',
                        letterSpacing: '0.05em',
                        margin: 0
                    }}>
                        CONFIRMED STOPPAGES
                    </p>
                </div>

                <div style={{ overflowY: 'auto', flex: 1 }}>
                    {stoppages.map(s => (
                        <div
                            key={s.id}
                            onClick={() => setSelectedStoppage(s)}
                            style={{
                                padding: '12px 20px',
                                borderBottom: '1px solid #0f172a',
                                cursor: 'pointer',
                                background: selectedStoppage?.id === s.id
                                    ? '#0f172a'
                                    : 'transparent',
                                transition: 'background 0.15s'
                            }}
                        >
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'flex-start'
                            }}>
                                <div>
                                    <span style={{
                                        color: '#f8fafc',
                                        fontSize: '12px',
                                        fontWeight: '500'
                                    }}>
                                        {s.vehicle_name}
                                    </span>
                                    <p style={{
                                        color: '#64748b',
                                        fontSize: '11px',
                                        margin: '2px 0 0'
                                    }}>
                                        {formatTime(s.started_at)}
                                    </p>
                                </div>
                                <span style={{
                                    background: '#ef444420',
                                    color: '#f87171',
                                    fontSize: '11px',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    fontWeight: '600'
                                }}>
                                    {formatDuration(s.duration_seconds)}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Map */}
            <div style={{ flex: 1, position: 'relative' }}>
                {loading && (
                    <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        color: '#94a3b8',
                        zIndex: 1000,
                        fontSize: '14px'
                    }}>
                        Loading map data...
                    </div>
                )}

                <MapContainer
                    center={mapCenter}
                    zoom={14}
                    style={{ height: '100%', width: '100%' }}
                >
                    <TileLayer
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        attribution='&copy; OpenStreetMap contributors'
                    />

                    {/* Trip route */}
                    {pathPositions.length > 1 && (
                        <Polyline
                            positions={pathPositions}
                            color="#3b82f6"
                            weight={3}
                            opacity={0.7}
                        />
                    )}

                    {/* Vehicle markers */}
                    {vehicles.map(v => (
                        v.lat && v.lng && (
                            <Marker
                                key={v.id}
                                position={[v.lat, v.lng]}
                                icon={vehicleIcon}
                            >
                                <Popup>
                                    <strong>{v.name}</strong><br />
                                    Last seen: {formatDateTime(v.last_seen)}
                                </Popup>
                            </Marker>
                        )
                    ))}

                    {/* Stoppage markers */}
                    {stoppages.map(s => (
                        s.lat && s.lng && (
                            <Marker
                                key={s.id}
                                position={[s.lat, s.lng]}
                                icon={stoppageIcon}
                                eventHandlers={{
                                    click: () => setSelectedStoppage(s)
                                }}
                            >
                                <Popup>
                                    <strong>{s.vehicle_name}</strong><br />
                                    Duration: {formatDuration(s.duration_seconds)}<br />
                                    Started: {formatTime(s.started_at)}<br />
                                    Ended: {formatTime(s.ended_at)}<br />
                                    Status: {s.status}
                                </Popup>
                            </Marker>
                        )
                    ))}
                </MapContainer>

                {/* Selected stoppage detail card */}
                {selectedStoppage && (
                    <div style={{
                        position: 'absolute',
                        bottom: '24px',
                        right: '24px',
                        background: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '10px',
                        padding: '16px',
                        width: '260px',
                        zIndex: 1000,
                        boxShadow: '0 4px 24px rgba(0,0,0,0.4)'
                    }}>
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            marginBottom: '12px'
                        }}>
                            <span style={{
                                color: '#f8fafc',
                                fontWeight: '600',
                                fontSize: '13px'
                            }}>
                                Stoppage Detail
                            </span>
                            <button
                                onClick={() => setSelectedStoppage(null)}
                                style={{
                                    background: 'transparent',
                                    border: 'none',
                                    color: '#64748b',
                                    cursor: 'pointer',
                                    fontSize: '16px'
                                }}
                            >
                                ×
                            </button>
                        </div>
                        {[
                            { label: 'Vehicle', value: selectedStoppage.vehicle_name },
                            { label: 'Duration', value: formatDuration(selectedStoppage.duration_seconds) },
                            { label: 'Started', value: formatTime(selectedStoppage.started_at) },
                            { label: 'Ended', value: formatTime(selectedStoppage.ended_at) },
                            { label: 'Status', value: selectedStoppage.status },
                        ].map(item => (
                            <div key={item.label} style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                marginBottom: '8px'
                            }}>
                                <span style={{ color: '#64748b', fontSize: '12px' }}>
                                    {item.label}
                                </span>
                                <span style={{
                                    color: '#f8fafc',
                                    fontSize: '12px',
                                    fontWeight: '500'
                                }}>
                                    {item.value}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}