import Navbar from '@/app/lib/Navbar';
 
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col md:flex-row overflow-hidden ">
      <div className=" max-w-screen max-h-dvh mx-auto w-full md:mr-[-8] not-last:md:w-64 ">
        <Navbar />
      </div>
        <div className="overflow-y-auto md:h-[calc(100vh-35px)] mt-12 md:mt-4 mr-4  w-screen bg-orange-200 rounded-md flex-grow p-4 md:p-12 scrollbar-hide-safe">{children}</div>
      </div>
  );
}
