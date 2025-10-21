import { Icons } from 'next/dist/lib/metadata/types/metadata-types';
import Image from 'next/image';

export const MainIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Dumbjared.png"
            width={60}
            height={60}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 

export const HomeIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Dumbjared.png"
            width={45}
            height={45}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const StatsIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Dumbjared.png"
            width={45}
            height={45}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const ChartsIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/DumbJared.png"
            width={45}
            height={45}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const OpiniometerIcon = ({ src="/Opiniometer.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Opiniometer.png"
            width={45}
            height={45}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const TestIcon = ({ src="/DumbJared-glossary.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/DumbJared-glossary.png"
            width={45}
            height={45}
            className="hidden md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}