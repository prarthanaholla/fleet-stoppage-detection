import { useState } from 'react'
import axios from 'axios'

export default function Login({ onLogin }) {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const handleLogin = async () => {
        setLoading(true)
        setError('')
        try {
            const response = await axios.post(
                'http://localhost:8000/api/v1/auth/login',
                { email, password }
            )
            const token = response.data.access_token
            localStorage.setItem('token', token)
            onLogin(token)
        } catch (err) {
            setError('Invalid email or password')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100vh',
            backgroundColor: '#0f172a'
        }}>
            <div style={{
                background: '#1e293b',
                padding: '40px',
                borderRadius: '12px',
                width: '360px',
                boxShadow: '0 4px 24px rgba(0,0,0,0.4)'
            }}>
                <h1 style={{
                    color: '#f8fafc',
                    fontSize: '22px',
                    marginBottom: '6px'
                }}>
                    Fleet Monitor
                </h1>
                <p style={{
                    color: '#94a3b8',
                    fontSize: '13px',
                    marginBottom: '28px'
                }}>
                    Stoppage Detection System
                </p>

                <div style={{ marginBottom: '16px' }}>
                    <label style={{ color: '#94a3b8', fontSize: '12px' }}>
                        EMAIL
                    </label>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="prarthana@porter.in"
                        style={{
                            width: '100%',
                            padding: '10px 12px',
                            marginTop: '6px',
                            background: '#0f172a',
                            border: '1px solid #334155',
                            borderRadius: '8px',
                            color: '#f8fafc',
                            fontSize: '14px',
                            boxSizing: 'border-box'
                        }}
                    />
                </div>

                <div style={{ marginBottom: '24px' }}>
                    <label style={{ color: '#94a3b8', fontSize: '12px' }}>
                        PASSWORD
                    </label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                        style={{
                            width: '100%',
                            padding: '10px 12px',
                            marginTop: '6px',
                            background: '#0f172a',
                            border: '1px solid #334155',
                            borderRadius: '8px',
                            color: '#f8fafc',
                            fontSize: '14px',
                            boxSizing: 'border-box'
                        }}
                    />
                </div>

                {error && (
                    <p style={{
                        color: '#f87171',
                        fontSize: '13px',
                        marginBottom: '16px'
                    }}>
                        {error}
                    </p>
                )}

                <button
                    onClick={handleLogin}
                    disabled={loading}
                    style={{
                        width: '100%',
                        padding: '11px',
                        background: loading ? '#334155' : '#3b82f6',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '14px',
                        fontWeight: '600',
                        cursor: loading ? 'not-allowed' : 'pointer'
                    }}
                >
                    {loading ? 'Signing in...' : 'Sign In'}
                </button>
            </div>
        </div>
    )
}