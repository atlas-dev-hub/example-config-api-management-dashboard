# System Monitor Configuration API – Certificate Generation Notes

**Date:** 10 April 2026  
**Purpose:** Record the exact steps followed to generate and export a local self-signed certificate for the **System Monitor Configuration API** test setup.

---

## Background

The Configuration API is documented internally as a **gRPC API over HTTPS** on top of the System Monitor Active-X API. Internal notes and tickets also mention:

- the API uses **HTTPS** and needs certificate setup,
- the VM needs **.NET 6 runtime** for the Configuration API child process,
- the API child process can fail silently and the **log file** is the reliable place to diagnose startup failures,
- example/test client documentation refers to **PFX + password** certificates.  

Relevant references found during troubleshooting:

- Internal notes / requirement for Configuration API certificate setup and `dotnet dev-certs` guidance.  
- Internal tasks / bugs stating the API runs as `SysMonConfigurationService.exe`, may fail without useful UI feedback, and that SSL certificate handling has known issues.  
- Microsoft documentation for:
  - `New-SelfSignedCertificate`
  - `Export-PfxCertificate`
  - PowerShell `Cert:` certificate provider

---

## What we verified before generating the certificate

### 1) VM network reachability
The VM **was reachable by ping**, so the issue was **not** basic IP connectivity.

### 2) Configuration API port not listening
We checked the VM for listening ports and confirmed that **TCP 5001 was not listening**.

This showed that the problem was **not just VPN/network access**. The Configuration API service itself was **not bound to port 5001** at that point.

### 3) `dotnet dev-certs` could not be used on this VM
We checked the installed runtimes:

```powershell
dotnet --list-runtimes
```

The VM had .NET runtimes installed, including **6.0** and **8.0** runtimes.

However, these commands showed that **no .NET SDK** was installed:

```powershell
dotnet dev-certs https --trust
dotnet --list-sdks
```

`dotnet dev-certs` failed because it is a **.NET SDK command**, and the VM had **no SDKs installed**.

Because of that, we switched to **PowerShell certificate-store based creation**.

---

## Certificate generation process that worked

### Step 1) Confirm no existing `localhost` certificate for the current user
We checked the current user certificate store:

```powershell
Get-ChildItem Cert:\CurrentUser\My |
    Where-Object Subject -like '*CN=localhost*' |
    Format-List Subject,Thumbprint,HasPrivateKey,NotAfter
```

At that time, **nothing was listed**, confirming that no `localhost` certificate was present for the current user.

---

### Step 2) Create a self-signed certificate in the Windows certificate store
We created a new self-signed certificate with PowerShell:

```powershell
$Certificate = New-SelfSignedCertificate -DnsName "localhost" -CertStoreLocation Cert:\CurrentUser\My
```

This stores the certificate in the **Windows certificate store**, not in a normal filesystem folder.

### What `Cert:\CurrentUser\My` means
This is **not a normal directory** like `C:\Temp`.  
It is a **PowerShell path into the Windows certificate store**:

- `Cert:` → PowerShell certificate provider
- `CurrentUser` → certificates for the current logged-in user
- `My` → the user’s Personal certificate store

---

### Step 3) Verify the certificate was created correctly
We then verified the newly created certificate:

```powershell
Get-ChildItem Cert:\CurrentUser\My |
    Where-Object Subject -like '*CN=localhost*' |
    Format-List Subject,Thumbprint,HasPrivateKey,NotAfter
```

The resulting certificate details were:

```text
Subject       : CN=localhost
Thumbprint    : 2A63BF5D4A3E91DE1A634DA64A5E89505D06E26A
HasPrivateKey : True
NotAfter      : 10/04/2027 14:18:29
```

This confirmed:

- the certificate exists,
- it is for **CN=localhost**,
- it has a **private key**,
- it is valid until **10/04/2027 14:18:29**.

---

## Exporting the certificate to a normal folder (worked)

Because System Monitor’s UI needs a **PFX file path**, we exported the certificate from the certificate store to a **normal file** on the Desktop.

### Step 4) Create a password object
```powershell
$pwd = ConvertTo-SecureString -String "ChangeThisPassword123!" -Force -AsPlainText
```

### Step 5) Export the certificate with its private key to a `.pfx`
```powershell
Export-PfxCertificate \
    -Cert "Cert:\CurrentUser\My\2A63BF5D4A3E91DE1A634DA64A5E89505D06E26A" \
    -FilePath "$env:USERPROFILE\Desktop\localhost.pfx" \
    -Password $pwd
```

### Result
The export succeeded and created:

```text
C:\Users\carles.abella\Desktop\localhost.pfx
```

This is the file that can be used in the System Monitor Configuration API setup UI.

---

## Values to use in System Monitor Configuration API Setup

### Certificate file
```text
C:\Users\carles.abella\Desktop\localhost.pfx
```

### Password
```text
ChangeThisPassword123!
```

---

## Important observations from the troubleshooting session

### What **did** work
- VM reachable by `ping`
- Self-signed `localhost` certificate successfully created
- Certificate confirmed to have a private key
- PFX export to Desktop succeeded

### What **did not** yet prove API startup
Even after the PFX was created and configured, the following check still returned **nothing**:

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -eq 5001
```

That means **port 5001 was still not listening**, so the certificate generation itself worked, but the **Configuration API service still was not successfully bound**.

---

## Interpretation

The certificate generation/export process itself was successful and reusable.

However, if the Configuration API still does not listen on port **5001** after pointing System Monitor to the PFX and restarting, the next step is **not to regenerate the certificate again**.

The next diagnostic step is to inspect the **System Monitor log** for entries containing:

```text
Configuration API
```

The internal notes indicate the log is the reliable place to confirm whether the Configuration API child process:

- launched successfully,
- failed to start,
- or terminated with an error.

---

## Final command summary

### Create certificate
```powershell
$Certificate = New-SelfSignedCertificate -DnsName "localhost" -CertStoreLocation Cert:\CurrentUser\My
```

### Verify certificate
```powershell
Get-ChildItem Cert:\CurrentUser\My |
    Where-Object Subject -like '*CN=localhost*' |
    Format-List Subject,Thumbprint,HasPrivateKey,NotAfter
```

### Create password object
```powershell
$pwd = ConvertTo-SecureString -String "ChangeThisPassword123!" -Force -AsPlainText
```

### Export to PFX on Desktop
```powershell
Export-PfxCertificate \
    -Cert "Cert:\CurrentUser\My\2A63BF5D4A3E91DE1A634DA64A5E89505D06E26A" \
    -FilePath "$env:USERPROFILE\Desktop\localhost.pfx" \
    -Password $pwd
```

### Check whether API is listening on 5001
```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -eq 5001
```

---