import Cairo from "gi://cairo?version=1.0";

export const dummyRegion = new Cairo.Region();
export const enable_click_through = (self) => self.input_shape_combine_region(dummyRegion);
