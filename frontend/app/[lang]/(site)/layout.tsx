import { Coque } from "@/components/app/coque"

export default function LayoutSite({ children }: LayoutProps<"/">) {
  return <Coque>{children}</Coque>
}
