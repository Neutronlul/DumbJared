import Navbar from '@/app/lib/Navbar';
 
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col md:flex-row md:overflow-hidden">
      <div className="max-w-screen max-h-screen mx-auto md:w-64">
        <Navbar />
      </div>
      <div className="mt-4 mb-4 w-screen overflow-x-hidden bg-linear-to-br from-yellow-200 to-pink-500 rounded-md flex-grow p-4 md:overflow-y-auto md:p-12">{children}</div>
    </div>
  );
}