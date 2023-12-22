# Build image
FROM golang:1.17-alpine3.15 as builder
RUN mkdir /build
WORKDIR /build

# Pull in files and get dependencies
COPY src/* .
RUN go mod download

# CGO_ENABLED: https://pkg.go.dev/cmd/cgo
RUN CGO_ENABLED=0 GOOS=linux go build -o dist/

# Final image
FROM alpine:3.15
COPY --from=builder /build/dist/blob_to_share /
CMD ["/blob_to_share"]