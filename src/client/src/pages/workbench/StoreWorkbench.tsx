import { useAuth } from '../../App';
import { logout } from '../../api/client';
import { openSettings } from '../../components/SettingsDialog';
import SimpleWorkbench from './SimpleWorkbench';
import WorkbenchChat from './WorkbenchChat';

/** Production bindings stay outside the public demo's shared presentation. */
export default function StoreWorkbench() {
  const viewer = useAuth();
  return <SimpleWorkbench viewer={viewer} ChatComponent={WorkbenchChat}
    onSettings={() => openSettings()}
    onLogout={() => { void logout().then(() => { location.href = '/login'; }); }} />;
}
