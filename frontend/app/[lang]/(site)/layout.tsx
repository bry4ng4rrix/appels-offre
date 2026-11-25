import { Coque } from "@/components/app/coque"

export default function LayoutSite({ children }: LayoutProps<"/[lang]">) {
  return <Coque>{children}</Coque>
}
