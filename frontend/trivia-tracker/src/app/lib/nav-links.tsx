'use client';

import { StatsIcon, HomeIcon, ChartsIcon, OpiniometerIcon, TestIcon} from '@/app/lib/Icons';
import Link from 'next/link';
import {usePathname} from 'next/navigation'
import clsx from 'clsx';

const links = [
  { name: 'Home', href: '/', icon: HomeIcon },
  { name: 'Stats', href: '/stats', icon: StatsIcon,},
  { name: 'Charts', href: '/charts', icon: ChartsIcon },
  { name: 'Opiniometer', href: '/opiniometer', icon:OpiniometerIcon},
  { name: 'Glossary', href: '/glossary', icon:TestIcon}
];

export default function NavLinks() {
  const pathname = usePathname();
 
  return (
    <>
      {links.map((link) => {
        const LinkIcon = link.icon;
        return (
          <Link
            key={link.name}
            href={link.href}
            className={clsx('flex h-[48px] grow items-center justify-center gap-2 rounded-md bg-orange-200 p-3 text-2xl font-medium hover:bg-sky-100 hover:text-blue-600 md:flex-none md:justify-start md:p-2 md:px-3',
              {'bg-yellow-200 text-black': pathname === link.href,},
            )}
          >
            <LinkIcon className="w-6" />
            <p className="hidden md:block">{link.name}</p>
          </Link>
        );
      })}
    </>
  );
}
