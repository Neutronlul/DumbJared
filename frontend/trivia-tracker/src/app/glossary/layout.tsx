import Navbar from '@/app/lib/Navbar';
 
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col md:flex-row ">
      <div className="max-w-screen mx-auto md:w-64 ml-">
        <Navbar />
      </div>
      <div className="mt-4 mr-2 mb-4 w-full overflow-hidden bg-orange-200 rounded-md flex-grow p-4 md:p-12">{children}</div>
    </div>
  );
}
