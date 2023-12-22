package main

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"net/url"
	"os"
	"strings"

	"github.com/Azure/azure-pipeline-go/pipeline"
	"github.com/Azure/azure-sdk-for-go/sdk/storage/azblob"
	"github.com/Azure/azure-storage-file-go/azfile"
)

// Find an environment variable, or throw an error if it doesn't yet exist
func findEnvVar(name string) string {
	res, found := os.LookupEnv(name)
	if !found {
		log.Fatal(fmt.Sprintf("Environment variable %s not found!", name))
	}
	return res
}

func contains(slice []string, toFind string) bool {
	for _, entry := range slice {
		if entry == toFind {
			return true
		}
	}
	return false
}

func checkAndCreateFolder(ctx *context.Context, azFilePipeline *pipeline.Pipeline, baseUrl string, folderPath string) {
	directoryParsedURL, _ := url.Parse(baseUrl + "/" + folderPath)
	fmt.Printf("    Checking directory '%s' exists . . . \n", folderPath)
	directoryURL := azfile.NewDirectoryURL(*directoryParsedURL, *azFilePipeline)
	_, err := directoryURL.GetProperties(*ctx)
	if err != nil {
		// Directory must not exist

		fmt.Printf("    Creating directory '%s' . . . \n", folderPath)
		directoryURL.Create(*ctx, azfile.Metadata{},
			azfile.SMBProperties{})
	}
}

func checkFolderAgainstBlobs(ctx *context.Context, azFilePipeline *pipeline.Pipeline, allBlobs *[]string, baseUrl string, folderPath string) {

	fmt.Printf(" - Folder /%s\n", folderPath)

	directoryParsedURL, _ := url.Parse(baseUrl + "/" + folderPath)
	directoryURL := azfile.NewDirectoryURL(*directoryParsedURL, *azFilePipeline)

	// List the file(s) and directory(s) in our share's root directory; since a directory may hold millions of files and directories, this is done 1 segment at a time.
	for marker := (azfile.Marker{}); marker.NotDone(); { // The parentheses around azfile.Marker{} are required to avoid compiler error.
		// Get a result segment starting with the file indicated by the current Marker.
		listResponse, err := directoryURL.ListFilesAndDirectoriesSegment(*ctx, marker, azfile.ListFilesAndDirectoriesOptions{})
		if err != nil {
			log.Fatal(err)
		}
		// Process the files returned in this result segment (if the segment is empty, the loop body won't execute)
		for _, fileEntry := range listResponse.FileItems {
			filePath := fileEntry.Name
			if len(folderPath) > 0 {
				filePath = folderPath + "/" + filePath
			}

			fmt.Printf("   - File /%s . . . ", filePath)

			if contains(*allBlobs, filePath) {
				fmt.Print("good\n")
			} else {

				fileURL := directoryURL.NewFileURL(fileEntry.Name)

				// Delete the file not in the blob
				_, err = fileURL.Delete(*ctx)
				if err != nil {
					log.Fatal(err)
				}

				fmt.Print("deleted\n")

			}

		}

		// For any sub-folder, do the same
		for _, folderEntry := range listResponse.DirectoryItems {
			newFolderPath := folderEntry.Name
			if len(folderPath) > 0 {
				newFolderPath = folderPath + "/" + newFolderPath
			}

			checkFolderAgainstBlobs(ctx, azFilePipeline, allBlobs, baseUrl, newFolderPath)
		}

		// IMPORTANT: ListFilesAndDirectoriesSegment returns the start of the next segment; you MUST use this to get
		// the next segment (after processing the current result segment).
		marker = listResponse.NextMarker
	}

}

func main() {

	// Get the credentials for this account
	accountName, accountKey := findEnvVar("ACCOUNT_NAME"), findEnvVar("ACCOUNT_KEY")
	containerName, shareName := findEnvVar("CONTAINER_NAME"), findEnvVar("SHARE_NAME")

	blobCredential, err := azblob.NewSharedKeyCredential(accountName, accountKey)
	if err != nil {
		log.Fatal("Invalid credentials with error: " + err.Error())
	}
	fileCredential, err := azfile.NewSharedKeyCredential(accountName, accountKey)
	if err != nil {
		log.Fatal(err)
	}
	azFilePipeline := azfile.NewPipeline(fileCredential, azfile.PipelineOptions{})

	blobBaseUrl := fmt.Sprintf("https://%s.blob.core.windows.net/", accountName)
	fileBaseUrl := fmt.Sprintf("https://%s.file.core.windows.net/", accountName)

	serviceClient, err := azblob.NewServiceClientWithSharedKey(blobBaseUrl, blobCredential, nil)
	if err != nil {
		log.Fatal("Invalid credentials with error: " + err.Error())
	}
	shareBaseUrl := fileBaseUrl + shareName

	// List the blobs in the container
	fmt.Println("Listing the blobs in the container:")
	containerClient := serviceClient.NewContainerClient(containerName)
	pager := containerClient.ListBlobsFlat(nil)

	ctx := context.Background()

	// List of all the blobs to upload
	allBlobs := []string{}

	// For each page
	for pager.NextPage(ctx) {
		resp := pager.PageResponse()

		// For each blob on the page
		for _, v := range resp.ContainerListBlobFlatSegmentResult.Segment.BlobItems {
			fmt.Println("  - " + *v.Name)
			allBlobs = append(allBlobs, *v.Name)

			blobClient, err := azblob.NewBlockBlobClientWithSharedKey(blobBaseUrl+containerName+"/"+*v.Name, blobCredential, nil)
			if err != nil {
				log.Fatal(err)
			}

			// Download the blob
			get, err := blobClient.Download(ctx, nil)
			if err != nil {
				log.Fatal(err)
			}

			downloadedData := &bytes.Buffer{}
			reader := get.Body(nil)
			numBytes, err := downloadedData.ReadFrom(reader)
			if err != nil {
				log.Fatal(err)
			}
			err = reader.Close()
			if err != nil {
				log.Fatal(err)
			}

			// Check that the folder exists
			splitPath := strings.Split(*v.Name, "/")
			numParts := len(splitPath)
			if numParts > 1 {

				// Need to create these folders
				for idx := 1; idx < numParts; idx++ {
					folderPath := strings.Join(splitPath[:idx], "/")

					checkAndCreateFolder(&ctx, &azFilePipeline, shareBaseUrl, folderPath)
				}
			}

			// Upload to the file share
			u, _ := url.Parse(fmt.Sprintf(fileBaseUrl + shareName + "/" + *v.Name))

			fileURL := azfile.NewFileURL(*u, azFilePipeline)

			// Trigger parallel upload with Parallelism set to 3. Note if there is an Azure file
			// with same name exists, UploadBufferToAzureFile will overwrite the existing Azure file with new content,
			// and set specified azfile.FileHTTPHeaders and Metadata.
			err = azfile.UploadBufferToAzureFile(ctx, downloadedData.Bytes(), fileURL,
				azfile.UploadToAzureFileOptions{
					Parallelism: 3,
					FileHTTPHeaders: azfile.FileHTTPHeaders{
						CacheControl: "no-transform",
					},
					Metadata: azfile.Metadata{},
					// If Progress is non-nil, this function is called periodically as bytes are uploaded.
					Progress: func(bytesTransferred int64) {
						fmt.Printf("    Uploaded %d of %d bytes.\n", bytesTransferred, numBytes)
					},
				})
			if err != nil {
				log.Fatal(err)
			}

		}

	}

	// Remove any files in the share that are not in the blob container
	fmt.Println("Checking the share files correspond to blobs:")
	checkFolderAgainstBlobs(&ctx, &azFilePipeline, &allBlobs, shareBaseUrl, "")

}
