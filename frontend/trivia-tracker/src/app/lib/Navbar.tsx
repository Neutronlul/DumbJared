
import NavLinks from '@/app/lib/nav-links';


export default function SideNav() {
  return (
    <div className="flex h-full flex-col px-3 py-4 md:px-2 p-1 w-60">
      <div className="text-center">
          <h1 className="text-4xl font-bold mb-2 rounded-md bg-orange-300 p-3">Dumb Jared</h1>
      </div>
      <div className="flex grow flex-row justify-between space-x-2 md:flex-col md:space-x-0 md:space-y-2">
        <NavLinks />
        <div className="hidden h-auto w-50 grow rounded-md bg-orange-200 md:block"></div>
      </div>
    </div>
  );
}


