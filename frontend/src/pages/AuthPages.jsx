import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await login(form.email, form.password);
      navigate(params.get('next') || '/account');
    } catch (err) {
      setError(err.response?.data?.non_field_errors?.[0] || 'Invalid email or password.');
    }
  };

  return (
    <AuthShell title="Login">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
        <Field label="Password" type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} />
        {error && <p className="text-signal text-xs font-mono">{error}</p>}
        <button className="w-full bg-ink text-paper py-4 font-display uppercase tracking-widest2 hover:bg-signal transition-colors">Login</button>
      </form>
      <p className="text-sm text-ink-soft mt-6">
        New here? <Link to="/register" className="underline text-ink">Create an account</Link>
      </p>
    </AuthShell>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', phone: '', password: '', confirm_password: '' });
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await register(form);
      navigate('/account');
    } catch (err) {
      const data = err.response?.data;
      setError(data ? Object.values(data).flat().join(' ') : 'Could not create account.');
    }
  };

  return (
    <AuthShell title="Create Account">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="First Name" value={form.first_name} onChange={(v) => setForm({ ...form, first_name: v })} />
          <Field label="Last Name" value={form.last_name} onChange={(v) => setForm({ ...form, last_name: v })} />
        </div>
        <Field label="Email" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
        <Field label="Phone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
        <Field label="Password" type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} />
        <Field label="Confirm Password" type="password" value={form.confirm_password} onChange={(v) => setForm({ ...form, confirm_password: v })} />
        {error && <p className="text-signal text-xs font-mono">{error}</p>}
        <button className="w-full bg-ink text-paper py-4 font-display uppercase tracking-widest2 hover:bg-signal transition-colors">Create Account</button>
      </form>
      <p className="text-sm text-ink-soft mt-6">
        Already have an account? <Link to="/login" className="underline text-ink">Login</Link>
      </p>
    </AuthShell>
  );
}

function AuthShell({ title, children }) {
  return (
    <div className="max-w-md mx-auto px-4 py-20">
      <h1 className="font-display text-3xl uppercase mb-8 text-center">{title}</h1>
      {children}
    </div>
  );
}

function Field({ label, type = 'text', value, onChange }) {
  return (
    <label className="block">
      <span className="text-xs font-mono uppercase tracking-widest2 text-ink-soft">{label}</span>
      <input
        type={type} required value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full border-b border-line focus:border-ink outline-none py-2 mt-1 bg-transparent"
      />
    </label>
  );
}
