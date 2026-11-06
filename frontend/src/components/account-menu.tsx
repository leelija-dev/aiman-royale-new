'use client';
import Link from 'next/link';
import {usePathname, useRouter} from 'next/navigation';
import {useEffect, useRef, useState} from 'react';
import {LayoutDashboard, Package, Heart, Ruler, Settings, LogOut, UserRound, CalendarDays} from 'lucide-react';
import {api, authChanged, bagChanged} from '@/lib/client';

type Me = {name: string; first_name: string; email: string; avatar: string};

/** Header account button: person icon when signed out; profile photo (or first letter) with a menu when signed in. */
export function AccountMenu() {
  const [me, setMe] = useState<Me | null | undefined>(undefined), [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null), router = useRouter(), pathname = usePathname();
  useEffect(() => {
    const load = () => api<{user: Me | null}>('auth/me/').then(r => setMe(r.user)).catch(() => setMe(null));
    load();
    window.addEventListener('auth-changed', load); window.addEventListener('bag-changed', load);
    return () => { window.removeEventListener('auth-changed', load); window.removeEventListener('bag-changed', load); };
  }, [pathname]);
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => { if (e instanceof KeyboardEvent ? e.key === 'Escape' : !box.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', close); document.addEventListener('keydown', close);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', close); };
  }, [open]);

  if (!me) return <Link href="/login" className="icon hide-xs" aria-label="Sign in"><UserRound/></Link>;
  const initial = (me.first_name || me.name || me.email || '?').trim()[0]?.toUpperCase() || '?';
  async function signOut() {
    try { await api('auth/logout/', 'POST', {}); } catch {}
    setMe(null); setOpen(false); bagChanged(); authChanged(); router.push('/'); router.refresh();
  }
  const links: [string, string, React.ReactNode][] = [
    ['/account', 'Dashboard', <LayoutDashboard key="d" size={17}/>], ['/account/orders', 'Order History', <Package key="o" size={17}/>],
    ['/wishlist', 'Wishlist', <Heart key="w" size={17}/>], ['/account?tab=custom', 'Custom Requests', <Ruler key="c" size={17}/>],
    ['/account?tab=appointments', 'Appointments', <CalendarDays key="a" size={17}/>], ['/account?tab=profile', 'Settings', <Settings key="s" size={17}/>]];
  return <div className="acct-menu hide-xs" ref={box}>
    <button type="button" className="acct-btn" aria-label={`Account menu for ${me.name || me.email}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
      {me.avatar ? <img src={me.avatar} alt="" referrerPolicy="no-referrer" width={34} height={34}/> : <span>{initial}</span>}
    </button>
    {open && <div className="acct-drop" role="menu">
      <div className="acct-head">{me.avatar ? <img src={me.avatar} alt="" referrerPolicy="no-referrer" width={42} height={42}/> : <span>{initial}</span>}
        <div><strong>{me.name || 'My account'}</strong><small>{me.email}</small></div></div>
      {links.map(([href, label, icon]) => <Link key={href} href={href} role="menuitem" onClick={() => setOpen(false)}>{icon}{label}</Link>)}
      <button type="button" role="menuitem" className="acct-out" onClick={signOut}><LogOut size={17}/>Log out</button>
    </div>}
  </div>;
}
