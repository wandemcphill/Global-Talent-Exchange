import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { Loading } from "@/components/gtex/ui";

export default function PaymentCallback() {
  const [params] = useSearchParams();
  const [msg, setMsg] = useState("Verifying your Paystack payment");
  useEffect(() => {
    const ref = params.get("reference") || params.get("trxref");
    if (!ref) {
      setMsg("Missing payment reference.");
      return;
    }
    api
      .get(`/owner/deposits/verify/${ref}`)
      .then(({ data }) => {
        if (data.status === "success") window.location.href = "/app/finance?deposit=success";
        else setMsg("Payment was not successful. No coins were credited.");
      })
      .catch(() => setMsg("We could not verify this payment. If you were charged, contact support with your reference."));
  }, [params]);
  return (
    <div data-testid="payment-callback-page" className="flex min-h-screen items-center justify-center bg-[#070B11]">
      <Loading label={msg} />
    </div>
  );
}
